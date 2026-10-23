package de.eseidinger.odip.platform.ingestion.web

import de.eseidinger.odip.platform.ingestion.service.IngestionService
import de.eseidinger.odip.platform.publication.DatasetAccess
import de.eseidinger.odip.platform.publication.checkPublication
import jakarta.servlet.http.HttpServletRequest
import jakarta.validation.Valid
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController
import java.util.UUID

data class ReferenceInputRequest(val sourceId: UUID, @field:Valid val input: CompleteRunRequest)

@RestController
@RequestMapping("/api/v1")
class OperatorIngestionController(private val ingestion: IngestionService, private val access: DatasetAccess, private val jdbc: JdbcTemplate) {
    @GetMapping("/operator-pipeline-runs")
    fun runs(): List<PipelineRunResponse> = ingestion.list().map { PipelineRunResponse(it.id, requireNotNull(it.source).id, requireNotNull(it.source).name, it.status.name, it.requestedAt, it.startedAt, it.completedAt) }

    @GetMapping("/operator-pipeline-runs/{id}/artifacts")
    fun artifacts(@PathVariable id: UUID): List<RawArtifactResponse> = ingestion.artifacts(id).map { item ->
        val artifact = item.artifact
        val validation = item.validation
        RawArtifactResponse(
            artifact.id,
            artifact.storageUri,
            artifact.contentType,
            artifact.contentLength,
            artifact.checksumSha256,
            artifact.sourceVersion,
            artifact.retrievedAt,
            validation?.let { RawArtifactValidationResponse(it.status.name, it.detectedFormat, it.recordCount, it.schemaFingerprint, it.failureReason, it.validatedAt) },
        )
    }

    @PostMapping("/reference-inputs")
    @Transactional
    fun capture(request: HttpServletRequest, @Valid @RequestBody body: ReferenceInputRequest): Map<String, Any?> {
        val datasets = jdbc.queryForList("SELECT dataset_id FROM dataset_source WHERE source_id=?", UUID::class.java, body.sourceId).filterNotNull()
        checkPublication(datasets.any { access.allowed(access.principal(request), it, "INGEST") }, "forbidden", "Input capture requires ingestion permission", 403)
        val run = ingestion.queue(body.sourceId)
        val started = ingestion.start(run.id)
        ingestion.complete(run.id, body.input.copy(claimToken = started.claimToken))
        // Capture returns identifiers for the input just submitted; it does not
        // grant access to the source's other raw bytes or require a READ grant.
        val artifact = jdbc.queryForMap("SELECT id,checksum_sha256 FROM raw_artifact WHERE pipeline_run_id=?", run.id)
        return mapOf("runId" to run.id, "rawArtifactId" to artifact["id"], "sha256" to artifact["checksum_sha256"])
    }
}
