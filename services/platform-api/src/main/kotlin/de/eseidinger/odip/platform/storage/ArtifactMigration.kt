package de.eseidinger.odip.platform.storage

import de.eseidinger.odip.platform.publication.DatasetAccess
import de.eseidinger.odip.platform.publication.RoutedArtifactStorage
import de.eseidinger.odip.platform.publication.checkPublication
import jakarta.servlet.http.HttpServletRequest
import org.slf4j.LoggerFactory
import org.springframework.beans.factory.ObjectProvider
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

@Service
class ArtifactMigration(private val jdbc: JdbcTemplate, private val storage: RoutedArtifactStorage, private val access: DatasetAccess) {
    @Transactional
    fun raw(request: HttpServletRequest, id: UUID, apply: Boolean): Map<String, Any> {
        val row = jdbc.queryForList("SELECT source_id FROM raw_artifact WHERE id=? FOR UPDATE", id).firstOrNull()
        checkPublication(row != null, "not_found", "Artifact was not found", 404)
        access.requireSource(request, row!!["source_id"] as UUID, "INGEST")
        access.requireSource(request, row["source_id"] as UUID, "READ")
        val bytes = storage.readRaw(id) ?: throw storageFailure("storage_content_missing")
        val result = storage.migrate(storage.rawKey(id), id, null, null, bytes, apply)
        if (apply && result["status"] == "migrated") access.audit(access.principal(request), "raw_storage_migrated")
        return result
    }

    @Transactional
    fun publication(request: HttpServletRequest, id: UUID, artifact: String, apply: Boolean): Map<String, Any> {
        // Same parent lock as uploads/finalization/retention; no published rows
        // or manifest bytes are modified by the storage migration.
        val row = jdbc.queryForList("SELECT dataset_id FROM dataset_publication WHERE id=? FOR UPDATE", id).firstOrNull()
        checkPublication(row != null, "not_found", "Publication was not found", 404)
        val dataset = row!!["dataset_id"] as UUID
        access.require(request, dataset, "WRITE")
        access.require(request, dataset, "READ")
        val bytes = storage.read(id, artifact)
        checkPublication(bytes != null, "not_found", "Artifact was not found", 404)
        val result = storage.migrate(storage.publicationKey(id, artifact), null, id, artifact, bytes!!, apply)
        if (apply && result["status"] == "migrated") access.audit(access.principal(request), "publication_storage_migrated", dataset, id)
        return result
    }
}

data class MigrationRequest(val apply: Boolean = false)

@RestController
@RequestMapping("/api/v1/artifact-storage")
class ArtifactMigrationController(private val migration: ArtifactMigration) {
    @PostMapping("/raw/{id}/migrate")
    fun raw(request: HttpServletRequest, @PathVariable id: UUID, @RequestBody body: MigrationRequest) = migration.raw(request, id, body.apply)

    @PostMapping("/publications/{id}/artifacts/{artifact}/migrate")
    fun publication(request: HttpServletRequest, @PathVariable id: UUID, @PathVariable artifact: String, @RequestBody body: MigrationRequest) = migration.publication(request, id, artifact, body.apply)
}

@Service
class ArtifactObjectCleanup(private val jdbc: JdbcTemplate, private val stores: ObjectProvider<ObjectStore>) {
    private val logger = LoggerFactory.getLogger(javaClass)

    private fun event(id: Any?, started: Long, failed: Boolean) {
        // Diagnostics must never change a storage operation's outcome.
        runCatching {
            val builder = if (failed) logger.atWarn() else logger.atInfo()
            builder.addKeyValue("event", if (failed) "artifact_deletion_retry" else "artifact_deleted")
                .addKeyValue("operation_id", id)
                .addKeyValue("elapsed_ms", (System.nanoTime() - started) / 1000000)
                .log(if (failed) "Artifact deletion will retry" else "Artifact deletion completed")
        }
    }

    @Transactional
    fun clean() {
        val store = stores.ifAvailable ?: return
        val rows = jdbc.queryForList("SELECT * FROM artifact_object_deletion ORDER BY created_at LIMIT 100 FOR UPDATE SKIP LOCKED")
        rows.forEach { row ->
            val started = System.nanoTime()
            try {
                store.delete(ObjectReference(row["bucket"] as String, row["object_key"] as String, row["version_id"] as String, "", 0))
                jdbc.update("DELETE FROM artifact_object_deletion WHERE id=?", row["id"])
                event(row["id"], started, false)
            } catch (_: de.eseidinger.odip.platform.publication.PublicationError) {
                // Keep the outbox row; storage outages must not undo expiry.
                event(row["id"], started, true)
            }
        }
    }
}

@Service
class ArtifactObjectCleanupSchedule(private val cleanup: ArtifactObjectCleanup) {
    private val logger = LoggerFactory.getLogger(javaClass)

    @Scheduled(fixedDelay = 60000)
    fun run() {
        val started = System.nanoTime()
        try {
            cleanup.clean()
        } catch (_: Exception) {
            // Catch outside the transaction, including commit failures. The next
            // batch retries without the scheduler logging raw SQL/SDK exceptions.
            runCatching {
                logger.atError().addKeyValue("event", "artifact_cleanup_failed")
                    .addKeyValue("operation_id", UUID.randomUUID())
                    .addKeyValue("elapsed_ms", (System.nanoTime() - started) / 1000000)
                    .addKeyValue("error_code", "storage_cleanup_failed")
                    .log("Artifact cleanup batch failed")
            }
        }
    }
}
