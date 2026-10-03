package de.eseidinger.odip.platform.ingestion.web

import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import de.eseidinger.odip.platform.ingestion.service.IngestionService
import jakarta.validation.Valid
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.Pattern
import jakarta.validation.constraints.PositiveOrZero
import java.time.Instant
import java.util.UUID
import org.springframework.http.HttpStatus
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
    @GetMapping("/pipeline-runs/{runId}/job") fun job(@PathVariable runId: UUID) = ingestionService.job(runId)
    @PostMapping("/pipeline-runs/{runId}/started") fun start(@PathVariable runId: UUID) = ingestionService.start(runId).toResponse()
    @PostMapping("/pipeline-runs/{runId}/completed") fun complete(@PathVariable runId: UUID, @Valid @RequestBody request: CompleteRunRequest) = ingestionService.complete(runId, request).toResponse()
    @PostMapping("/pipeline-runs/{runId}/failed") fun fail(@PathVariable runId: UUID, @Valid @RequestBody request: FailRunRequest) = ingestionService.fail(runId, request.reason).toResponse()
}

data class CompleteRunRequest(@field:NotBlank @field:Pattern(regexp = "^s3://.+") val storageUri: String, val contentType: String? = null, @field:PositiveOrZero val contentLength: Long, @field:Pattern(regexp = "^[a-fA-F0-9]{64}$") val checksumSha256: String, val sourceVersion: String? = null)
data class FailRunRequest(@field:NotBlank val reason: String)
data class PipelineRunResponse(val id: UUID, val sourceId: UUID, val sourceName: String, val status: String, val requestedAt: Instant, val startedAt: Instant?, val completedAt: Instant?)
data class RawArtifactResponse(val id: UUID, val storageUri: String, val contentType: String?, val contentLength: Long, val checksumSha256: String, val sourceVersion: String?, val retrievedAt: Instant)
private fun PipelineRunEntity.toResponse() = PipelineRunResponse(id, requireNotNull(source).id, requireNotNull(source).name, status.name, requestedAt, startedAt, completedAt)
private fun RawArtifactEntity.toResponse() = RawArtifactResponse(id, storageUri, contentType, contentLength, checksumSha256, sourceVersion, retrievedAt)
