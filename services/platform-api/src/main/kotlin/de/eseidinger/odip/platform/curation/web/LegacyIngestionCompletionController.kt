package de.eseidinger.odip.platform.curation.web

import de.eseidinger.odip.platform.ingestion.service.IngestionService
import de.eseidinger.odip.platform.ingestion.service.TransformationRequest
import de.eseidinger.odip.platform.ingestion.web.CompleteRunRequest
import de.eseidinger.odip.platform.ingestion.web.ArtifactValidationRequest
import de.eseidinger.odip.platform.ingestion.web.PipelineRunResponse
import jakarta.validation.Valid
import jakarta.validation.constraints.NotEmpty
import org.springframework.web.bind.annotation.*
import java.util.UUID

// Compatibility mapping remains in the reference adapter, outside ingestion core.
data class LegacyCompleteRunRequest(@field:NotEmpty val payload: ByteArray, val contentType: String? = null,
    val contentLength: Long, val checksumSha256: String, val sourceVersion: String? = null,
    val validation: ArtifactValidationRequest? = null, val transformation: TransformationRequest? = null,
    val energyObservation: Map<String, Any?>? = null, val claimToken: UUID? = null)

@RestController
class LegacyIngestionCompletionController(private val ingestion: IngestionService) {
    @PostMapping("/api/pipeline-runs/{runId}/completed")
    fun complete(@PathVariable runId: UUID, @Valid @RequestBody body: LegacyCompleteRunRequest): PipelineRunResponse {
        val transform = body.transformation ?: body.energyObservation?.let { TransformationRequest("eurostat-renewable-share/v1", it) }
        val run = ingestion.complete(runId, CompleteRunRequest(body.payload, body.contentType, body.contentLength, body.checksumSha256, body.sourceVersion, body.validation, transform, body.claimToken))
        return PipelineRunResponse(run.id, requireNotNull(run.source).id, requireNotNull(run.source).name, run.status.name, run.requestedAt, run.startedAt, run.completedAt)
    }
}
