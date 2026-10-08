package de.eseidinger.odip.platform.ingestion.web

import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import de.eseidinger.odip.platform.ingestion.domain.ArtifactValidationStatus
import de.eseidinger.odip.platform.ingestion.service.IngestionService
import de.eseidinger.odip.platform.ingestion.service.RawArtifactWithValidation
import de.eseidinger.odip.platform.curation.web.CreateEnergyObservationRequest
import jakarta.validation.Valid
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotEmpty
import jakarta.validation.constraints.Pattern
import jakarta.validation.constraints.PositiveOrZero
import java.time.Instant
import java.util.UUID
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RestController

@RestController
@RequestMapping("/api")
class IngestionController(private val ingestionService: IngestionService) {
    @GetMapping("/pipeline-runs") fun list() = ingestionService.list().map { it.toResponse() }
    @GetMapping("/pipeline-runs/{runId}/artifacts") fun artifacts(@PathVariable runId: UUID) = ingestionService.artifacts(runId).map { it.toResponse() }
    @PostMapping("/data-sources/{sourceId}/ingestions")
    fun queue(@PathVariable sourceId: UUID): ResponseEntity<PipelineRunResponse> = ResponseEntity.status(HttpStatus.ACCEPTED).body(ingestionService.queue(sourceId).toResponse())
    @PostMapping("/pipeline-runs/claim-next")
    fun claimNext(): ResponseEntity<de.eseidinger.odip.platform.ingestion.service.IngestionJob> = ingestionService.claimNext()?.let { ResponseEntity.ok(it) } ?: ResponseEntity.noContent().build()
    @GetMapping("/pipeline-runs/{runId}/job") fun job(@PathVariable runId: UUID) = ingestionService.job(runId)
    @PostMapping("/pipeline-runs/{runId}/started") fun start(@PathVariable runId: UUID) = ingestionService.start(runId).toResponse()
    @PostMapping("/pipeline-runs/{runId}/completed") fun complete(@PathVariable runId: UUID, @Valid @RequestBody request: CompleteRunRequest) = ingestionService.complete(runId, request).toResponse()
    @PostMapping("/pipeline-runs/{runId}/failed") fun fail(@PathVariable runId: UUID, @Valid @RequestBody request: FailRunRequest) = ingestionService.fail(runId, request.reason).toResponse()
    @GetMapping("/raw-artifacts/{artifactId}/content")
    fun content(@PathVariable artifactId: UUID): ResponseEntity<ByteArray> {
        val artifact = ingestionService.artifactContent(artifactId)
        val payload = requireNotNull(artifact.payload) { "Raw artifact content is unavailable" }
        val contentType = artifact.contentType?.let { runCatching { MediaType.parseMediaType(it) }.getOrNull() } ?: MediaType.APPLICATION_OCTET_STREAM
        return ResponseEntity.ok().contentType(contentType).contentLength(artifact.contentLength).body(payload)
    }
}

data class CompleteRunRequest(@field:NotEmpty val payload: ByteArray, val contentType: String? = null, @field:PositiveOrZero val contentLength: Long, @field:Pattern(regexp = "^[a-fA-F0-9]{64}$") val checksumSha256: String, val sourceVersion: String? = null, @field:Valid val validation: ArtifactValidationRequest? = null, @field:Valid val energyObservation: CreateEnergyObservationRequest? = null)
data class ArtifactValidationRequest(val status: ArtifactValidationStatus, val detectedFormat: String? = null, @field:PositiveOrZero val recordCount: Long? = null, @field:Pattern(regexp = "^[a-fA-F0-9]{64}$") val schemaFingerprint: String? = null, val failureReason: String? = null)
data class FailRunRequest(@field:NotBlank val reason: String)
data class PipelineRunResponse(val id: UUID, val sourceId: UUID, val sourceName: String, val status: String, val requestedAt: Instant, val startedAt: Instant?, val completedAt: Instant?)
data class RawArtifactResponse(val id: UUID, val storageUri: String, val contentType: String?, val contentLength: Long, val checksumSha256: String, val sourceVersion: String?, val retrievedAt: Instant, val validation: RawArtifactValidationResponse?)
data class RawArtifactValidationResponse(val status: String, val detectedFormat: String?, val recordCount: Long?, val schemaFingerprint: String?, val failureReason: String?, val validatedAt: Instant)
private fun PipelineRunEntity.toResponse() = PipelineRunResponse(id, requireNotNull(source).id, requireNotNull(source).name, status.name, requestedAt, startedAt, completedAt)
private fun RawArtifactWithValidation.toResponse() = RawArtifactResponse(artifact.id, artifact.storageUri, artifact.contentType, artifact.contentLength, artifact.checksumSha256, artifact.sourceVersion, artifact.retrievedAt, validation?.let { RawArtifactValidationResponse(it.status.name, it.detectedFormat, it.recordCount, it.schemaFingerprint, it.failureReason, it.validatedAt) })
