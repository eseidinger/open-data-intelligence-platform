package de.eseidinger.odip.platform.publication

import com.fasterxml.jackson.databind.JsonNode
import jakarta.servlet.http.HttpServletRequest
import io.micrometer.core.instrument.MeterRegistry
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.scheduling.annotation.Scheduled
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.util.UUID

data class DraftRequest(val datasetId: UUID, val manifest: Map<String, Any?>, val rawArtifactIds: List<UUID> = emptyList())
data class ValidationReport(val manifestSha256: String, val policyRef: String, val checks: Map<String, String>, val artifactDigests: Map<String, String>, val failureCode: String? = null, val claimToken: UUID? = null)
data class GrantRequest(val principalId: String, val permission: String)
data class StoredPublication(val id: UUID, val datasetId: UUID, val manifest: ByteArray, val digest: String, val status: String, val creator: String, val validator: String?, val report: String?, val failureCode: String?)

@Service
class PublicationService(
    private val jdbc: JdbcTemplate, private val contracts: PublicationContracts,
    private val storage: ArtifactStorage, private val access: DatasetAccess, private val metrics: MeterRegistry,
) {
    private fun record(id: UUID, lock: Boolean = false): StoredPublication = jdbc.query(
        "SELECT * FROM dataset_publication WHERE id=?" + if (lock) " FOR UPDATE" else "",
        { row, _ -> StoredPublication(row.getObject("id", UUID::class.java), row.getObject("dataset_id", UUID::class.java), row.getBytes("manifest"), row.getString("manifest_sha256"), row.getString("status"), row.getString("creator"), row.getString("validator"), row.getString("report"), row.getString("failure_code")) }, id).firstOrNull()
        ?: reject(404, "not_found", "Publication was not found")

    private fun key(value: String) {
        checkPublication(value.length in 1..200 && value.all { it.code in 33..126 }, "invalid_idempotency_key", "Idempotency-Key must contain 1 to 200 visible ASCII characters", 400)
    }

    @Transactional
    fun create(request: HttpServletRequest, body: DraftRequest, key: String): Map<String, Any?> {
        key(key)
        access.require(request, body.datasetId, "WRITE")
        checkPublication(body.rawArtifactIds.size <= 100 && body.rawArtifactIds.distinct().size == body.rawArtifactIds.size,"invalid_lineage","At most 100 distinct input artifacts are supported",400)
        val principal = access.principal(request)
        val manifest = contracts.canonical(contracts.mapper.writeValueAsBytes(body.manifest))
        checkPublication(manifest.size <= 1048576, "payload_too_large", "Manifest exceeds 1 MiB", 413)
        val document = contracts.parse(manifest)
        contracts.validate("dataset-publication-v1", document)
        checkPublication(jdbc.queryForObject("SELECT NOT EXISTS(SELECT 1 FROM publication_support WHERE schema_ref=? AND support_ends_at < CURRENT_TIMESTAMP)",Boolean::class.java,document["schemaRef"].asText()) == true,"unsupported_schema","Profile support has ended")
        val policy = contracts.policy(document)
        val descriptors = document["artifacts"].toList()
        checkPublication(descriptors.map { it["artifactId"].asText() }.distinct().size == descriptors.size &&
            descriptors.map { it["role"].asText() }.distinct().size == descriptors.size &&
            descriptors.all { it["path"].asText() == "artifacts/${it["artifactId"].asText()}" }, "invalid_artifacts", "Artifact IDs, roles, and paths must be unique and consistent")
        checkPublication(descriptors.map { it["role"].asText() }.toSet() == policy["artifactSchemas"].fieldNames().asSequence().toSet(), "invalid_artifacts", "Artifacts must match the registered profile roles")
        val requestDigest = sha256(manifest + (body.datasetId.toString() + body.rawArtifactIds.sorted().joinToString()).toByteArray())
        jdbc.queryForObject("SELECT pg_advisory_xact_lock(hashtext(?)) IS NULL", Boolean::class.java, "$principal/$key")
        val previous = jdbc.queryForList("SELECT id,request_sha256 FROM dataset_publication WHERE creator=? AND idempotency_key=?", principal, key).firstOrNull()
        if (previous != null) {
            checkPublication(previous["request_sha256"] == requestDigest, "idempotency_conflict", "Idempotency key was already used with different content", 409)
            return summary(record(previous["id"] as UUID))
        }
        checkPublication(jdbc.queryForList("SELECT id FROM dataset WHERE id=? FOR UPDATE", body.datasetId).isNotEmpty(), "not_found", "Dataset was not found", 404)
        val publicId = document["datasetId"].asText()
        jdbc.update("INSERT INTO dataset_public_identity VALUES (?,?) ON CONFLICT DO NOTHING", publicId, body.datasetId)
        val identity = jdbc.queryForList("SELECT dataset_id FROM dataset_public_identity WHERE public_dataset_id=?", publicId).firstOrNull()
        checkPublication(identity?.get("dataset_id") == body.datasetId, "dataset_identity_conflict", "Public identifier is already bound to another dataset", 409)
        body.rawArtifactIds.forEach { raw ->
            checkPublication(jdbc.queryForList("SELECT r.id FROM raw_artifact r JOIN dataset_source ds ON ds.source_id=r.source_id WHERE r.id=? AND ds.dataset_id=? AND r.payload IS NOT NULL AND octet_length(r.payload)=r.content_length", raw, body.datasetId).isNotEmpty(), "invalid_lineage", "Input artifact must have captured bytes and belong to a contributing source")
        }
        val id = UUID.randomUUID()
        jdbc.update("INSERT INTO dataset_publication(id,dataset_id,public_dataset_id,version,manifest,manifest_sha256,status,creator,idempotency_key,request_sha256) VALUES (?,?,?,?,?,?,'DRAFT',?,?,?)",
            id, body.datasetId, publicId, document["version"].asText(), manifest, sha256(manifest), principal, key, requestDigest)
        body.rawArtifactIds.distinct().forEach { jdbc.update("INSERT INTO publication_input VALUES (?,?)", id, it) }
        access.audit(principal, "draft_created", body.datasetId, id)
        return summary(record(id))
    }

    @Transactional
    fun upload(request: HttpServletRequest, id: UUID, artifactId: String, bytes: ByteArray) {
        val record = record(id, true)
        access.require(request, record.datasetId, "WRITE")
        checkPublication(record.status == "DRAFT", "publication_locked", "Only draft artifacts can be uploaded", 409)
        checkPublication(bytes.size <= 10485760, "payload_too_large", "Artifact exceeds 10 MiB", 413)
        val manifest = contracts.parse(record.manifest)
        val descriptor = manifest["artifacts"].firstOrNull { it["artifactId"].asText() == artifactId } ?: reject(404, "not_found", "Artifact is not declared in this manifest")
        checkPublication(sha256(bytes) == descriptor["sha256"].asText(), "checksum_mismatch", "Artifact digest does not match the manifest")
        val previous = storage.read(id, artifactId)
        if (previous != null) {
            checkPublication(previous.contentEquals(bytes), "artifact_conflict", "Uploaded artifact is immutable", 409)
            return
        }
        val total = jdbc.queryForObject("SELECT COALESCE(SUM(octet_length(payload)),0) FROM publication_artifact WHERE publication_id=?", Long::class.java, id) ?: 0L
        checkPublication(total + bytes.size <= 52428800, "publication_limit_exceeded", "Publication exceeds 50 MiB")
        if (descriptor["mediaType"].asText() == "application/json") {
            checkPublication(contracts.canonical(bytes).contentEquals(bytes), "non_canonical_artifact", "JSON artifacts must use RFC 8785 canonical bytes")
            val policy = contracts.policy(manifest)
            val schema = policy["artifactSchemas"][descriptor["role"].asText()] ?: reject(422, "unsupported_schema", "Artifact role is not declared by its profile")
            contracts.validate(schema.asText(), contracts.parse(bytes))
        }
        storage.put(id, artifactId, bytes)
        access.audit(access.principal(request), "artifact_attached", record.datasetId, id)
    }

    @Transactional
    fun publish(request: HttpServletRequest, id: UUID, key: String): Map<String, Any?> {
        key(key)
        val publication = record(id, true)
        access.require(request, publication.datasetId, "WRITE")
        val principal = access.principal(request)
        jdbc.queryForObject("SELECT pg_advisory_xact_lock(hashtext(?)) IS NULL", Boolean::class.java, "publish/$principal/$key")
        val previous = jdbc.queryForList("SELECT publication_id FROM publication_request WHERE principal_id=? AND idempotency_key=?", principal, key).firstOrNull()
        if (previous != null) {
            checkPublication(previous["publication_id"] == id, "idempotency_conflict", "Publication key was already used for another draft", 409)
            return summary(publication)
        }
        checkPublication(publication.status == "DRAFT", "publication_locked", "Only a draft may request publication", 409)
        val manifest = contracts.parse(publication.manifest)
        checkPublication(manifest["artifacts"].all { storage.read(id, it["artifactId"].asText()) != null }, "missing_artifact", "All declared artifacts must be uploaded")
        jdbc.update("INSERT INTO publication_request VALUES (?,?,?)", id, principal, key)
        jdbc.update("UPDATE dataset_publication SET status='VALIDATING' WHERE id=?", id)
        access.audit(principal, "publication_requested", publication.datasetId, id)
        return summary(record(id))
    }

    @Transactional
    fun claim(request: HttpServletRequest): Map<String, Any?>? {
        val principal = access.principal(request)
        val ids = jdbc.queryForList("SELECT p.id FROM dataset_publication p WHERE status='VALIDATING' AND validator IS NULL AND (? OR EXISTS(SELECT 1 FROM dataset_grant g WHERE g.dataset_id=p.dataset_id AND g.principal_id=? AND g.permission='VALIDATE')) ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1", access.developmentBypass(), principal)
        val id = ids.firstOrNull()?.get("id") as UUID? ?: return null
        jdbc.update("UPDATE dataset_publication SET validator=?,claimed_at=CURRENT_TIMESTAMP,claim_token=? WHERE id=?", principal, UUID.randomUUID(), id)
        return summary(record(id))
    }

    @Transactional
    fun complete(request: HttpServletRequest, id: UUID, report: ValidationReport): Map<String, Any?> {
        val publication = record(id, true)
        val principal = access.principal(request)
        access.require(request, publication.datasetId, "VALIDATE")
        checkPublication(publication.validator == principal, "forbidden", "Only the claiming validator may submit evidence", 403)
        checkPublication(report.claimToken != null && jdbc.queryForObject("SELECT claim_token FROM dataset_publication WHERE id=?", UUID::class.java,id) == report.claimToken,
            "stale_claim", "The validation claim is no longer current",409)
        val reportJson = contracts.mapper.writeValueAsString(report)
        if (publication.status in setOf("PUBLISHED", "FAILED")) {
            checkPublication(publication.report?.let { contracts.parse(it.toByteArray()) } == contracts.parse(reportJson.toByteArray()), "validation_conflict", "Validation result is already final", 409)
            return summary(publication)
        }
        checkPublication(publication.status == "VALIDATING", "publication_locked", "Publication is not awaiting validation", 409)
        val manifest = contracts.parse(publication.manifest)
        val policy = contracts.policy(manifest)
        checkPublication(report.manifestSha256 == publication.digest && report.policyRef == policy["policyRef"].asText(), "validation_mismatch", "Evidence must identify the exact manifest and policy")
        val digests = manifest["artifacts"].associate { it["artifactId"].asText() to it["sha256"].asText() }
        checkPublication(report.artifactDigests == digests, "validation_mismatch", "Evidence must identify every artifact digest")
        val required = policy["checks"].map { it.asText() }.toSet()
        checkPublication(report.checks.keys == required && report.checks.values.all { it in setOf("PASS", "FAIL") }, "validation_mismatch", "Evidence must include every required check")
        val passed = report.failureCode == null && report.checks.values.all { it == "PASS" }
        checkPublication(report.failureCode == null || Regex("^[a-z][a-z0-9_]{0,99}$").matches(report.failureCode), "invalid_report", "Failure code is invalid")
        if (passed) {
            contracts.validate("dataset-publication-v1", manifest)
            manifest["artifacts"].forEach { descriptor ->
                val bytes = storage.read(id, descriptor["artifactId"].asText()) ?: reject(422, "missing_artifact", "Artifact is missing")
                checkPublication(sha256(bytes) == descriptor["sha256"].asText(), "checksum_mismatch", "Stored artifact failed integrity verification")
            }
        }
        jdbc.update("UPDATE dataset_publication SET status=?,report=?::jsonb,failure_code=?,published_at=? WHERE id=?",
            if (passed) "PUBLISHED" else "FAILED", reportJson, if (passed) null else report.failureCode ?: "quality_failed", if (passed) java.sql.Timestamp.from(Instant.now()) else null, id)
        access.audit(principal, if (passed) "publication_completed" else "publication_failed", publication.datasetId, id)
        metrics.counter("odip.publication.results", "status", if (passed) "published" else "failed").increment()
        val created = jdbc.queryForObject("SELECT created_at FROM dataset_publication WHERE id=?",java.sql.Timestamp::class.java,id)!!.toInstant()
        metrics.timer("odip.publication.duration").record(java.time.Duration.between(created,Instant.now()).coerceAtLeast(java.time.Duration.ZERO))
        return summary(record(id))
    }

    @Transactional(readOnly = true)
    fun drafts(request: HttpServletRequest): List<Map<String, Any?>> = jdbc.queryForList("SELECT id,dataset_id FROM dataset_publication ORDER BY created_at DESC")
        .filter { access.allowed(access.principal(request), it["dataset_id"] as UUID, "WRITE") || access.allowed(access.principal(request), it["dataset_id"] as UUID, "VALIDATE") }.map { summary(record(it["id"] as UUID)) }

    @Transactional(readOnly = true)
    fun draft(request: HttpServletRequest, id: UUID): Map<String, Any?> {
        val p = record(id)
        checkPublication(access.allowed(access.principal(request), p.datasetId, "WRITE") || access.allowed(access.principal(request), p.datasetId, "VALIDATE"), "forbidden", "Draft access is required", 403)
        return summary(p)
    }

    @Transactional(readOnly = true)
    fun draftArtifact(request: HttpServletRequest, id: UUID, artifact: String): ByteArray {
        val p = record(id)
        access.require(request, p.datasetId, "VALIDATE")
        return storage.read(id, artifact) ?: reject(404, "not_found", "Artifact was not found")
    }

    @Transactional(readOnly = true)
    fun operatorArtifact(request: HttpServletRequest, id: UUID, artifact: String): ByteArray {
        val p = record(id)
        access.require(request, p.datasetId, "WRITE")
        return storage.read(id, artifact) ?: reject(404, "not_found", "Artifact was not found")
    }

    @Transactional(readOnly = true)
    fun discover(request: HttpServletRequest, schemaRef: String?, page: Int, pageSize: Int): Map<String, Any> {
        checkPublication(page >= 0 && pageSize in 1..100, "invalid_pagination", "Page and pageSize are outside supported limits", 400)
        val principal = access.principal(request)
        val filter = "FROM dataset_publication p WHERE status='PUBLISHED' AND (? OR EXISTS(SELECT 1 FROM dataset_grant g WHERE g.dataset_id=p.dataset_id AND g.principal_id=? AND g.permission='READ')) AND (? IS NULL OR convert_from(manifest,'UTF8')::jsonb->>'schemaRef'=?)"
        val bypass = access.developmentBypass()
        // Explicit cast keeps a null schema filter typed in PostgreSQL.
        val typedFilter = filter.replace("? IS NULL", "CAST(? AS text) IS NULL")
        val count = jdbc.queryForObject("SELECT COUNT(*) $typedFilter",Long::class.java,bypass,principal,schemaRef,schemaRef) ?: 0L
        val records = jdbc.query("SELECT manifest $typedFilter ORDER BY public_dataset_id,version LIMIT ? OFFSET ?", { row, _ -> contracts.mapper.convertValue(contracts.parse(row.getBytes(1)),Map::class.java) }, bypass,principal,schemaRef,schemaRef,pageSize,page.toLong()*pageSize)
        return mapOf("items" to records, "page" to page, "pageSize" to pageSize, "total" to count)
    }

    @Transactional(readOnly = true)
    fun read(request: HttpServletRequest, dataset: String, version: String, artifact: String?): Pair<ByteArray, String> {
        val identity = jdbc.queryForList("SELECT dataset_id FROM dataset_public_identity WHERE public_dataset_id=?", dataset).firstOrNull() ?: reject(404, "not_found", "Dataset was not found")
        access.require(request, identity["dataset_id"] as UUID, "READ")
        val id = jdbc.queryForList("SELECT id FROM dataset_publication WHERE public_dataset_id=? AND version=?", dataset, version).firstOrNull()?.get("id") as UUID? ?: reject(404, "not_found", "Version was not found")
        val p = record(id)
        checkPublication(p.status == "PUBLISHED", "dataset_version_not_published", "Version is not published", 409)
        metrics.counter("odip.publication.retrievals").increment()
        if (artifact == null) return p.manifest to "application/json"
        val descriptor = contracts.parse(p.manifest)["artifacts"].firstOrNull { it["artifactId"].asText() == artifact } ?: reject(404, "not_found", "Artifact was not found")
        return (storage.read(id, artifact) ?: reject(404, "not_found", "Artifact was not found")) to descriptor["mediaType"].asText()
    }

    @Scheduled(fixedDelay = 60000)
    @Transactional
    fun recoverAbandoned() {
        jdbc.update("UPDATE dataset_publication SET validator=NULL,claimed_at=NULL,claim_token=NULL WHERE status='VALIDATING' AND claimed_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes'")
        jdbc.update("DELETE FROM publication_audit WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '180 days'")
        val expired = jdbc.queryForList("SELECT id FROM dataset_publication WHERE status='PUBLISHED' AND publication_expired(id)",UUID::class.java).filterNotNull()
        expired.forEach { id ->
            jdbc.update("DELETE FROM publication_request WHERE publication_id=?",id)
            jdbc.update("DELETE FROM publication_input WHERE publication_id=?",id)
            jdbc.update("DELETE FROM publication_artifact WHERE publication_id=?",id)
            access.audit("retention", "publication_expired",publication=id)
            jdbc.update("DELETE FROM dataset_publication WHERE id=?",id)
        }
    }

    private fun summary(p: StoredPublication): Map<String, Any?> = mapOf(
        "id" to p.id, "datasetId" to p.datasetId, "status" to p.status, "manifestSha256" to p.digest,
        "manifest" to contracts.mapper.convertValue(contracts.parse(p.manifest), Map::class.java),
        "report" to p.report?.let { contracts.mapper.convertValue(contracts.parse(it.toByteArray()), Map::class.java) }, "failureCode" to p.failureCode,
        "claimToken" to jdbc.queryForObject("SELECT claim_token FROM dataset_publication WHERE id=?",UUID::class.java,p.id),
        "inputArtifacts" to jdbc.query("SELECT a.id,a.pipeline_run_id,a.checksum_sha256,a.retrieved_at FROM raw_artifact a JOIN publication_input i ON i.raw_artifact_id=a.id WHERE i.publication_id=? ORDER BY a.id",
            { row, _ -> mapOf("rawArtifactId" to row.getObject(1,UUID::class.java), "pipelineRunId" to row.getObject(2,UUID::class.java), "sha256" to row.getString(3), "capturedAt" to row.getTimestamp(4).toInstant().toString()) },p.id))
}
