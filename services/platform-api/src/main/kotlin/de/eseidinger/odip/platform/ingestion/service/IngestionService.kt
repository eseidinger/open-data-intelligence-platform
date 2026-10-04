package de.eseidinger.odip.platform.ingestion.service

import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import de.eseidinger.odip.platform.curation.service.EnergyCurationService
import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import de.eseidinger.odip.platform.ingestion.domain.PipelineRunStatus
import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import de.eseidinger.odip.platform.ingestion.domain.RawArtifactValidationEntity
import de.eseidinger.odip.platform.ingestion.persistence.PipelineRunRepository
import de.eseidinger.odip.platform.ingestion.persistence.RawArtifactRepository
import de.eseidinger.odip.platform.ingestion.persistence.RawArtifactValidationRepository
import de.eseidinger.odip.platform.ingestion.web.CompleteRunRequest
import java.time.Instant
import java.util.UUID
import java.security.MessageDigest
import org.springframework.http.HttpStatus
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.server.ResponseStatusException

@Service
class IngestionService(
    private val dataSourceRepository: DataSourceRepository,
    private val pipelineRunRepository: PipelineRunRepository,
    private val rawArtifactRepository: RawArtifactRepository,
    private val rawArtifactValidationRepository: RawArtifactValidationRepository,
    private val energyCurationService: EnergyCurationService,
    @Value("\${odip.raw-artifact.max-payload-bytes}") private val maxPayloadBytes: Long,
) {
    @Transactional(readOnly = true)
    fun list(): List<PipelineRunEntity> = pipelineRunRepository.findAll().sortedByDescending { it.requestedAt }

    @Transactional(readOnly = true)
    fun artifacts(runId: UUID): List<RawArtifactWithValidation> {
        run(runId)
        return rawArtifactRepository.findAllByPipelineRun_IdOrderByRetrievedAtDesc(runId).map { artifact ->
            RawArtifactWithValidation(artifact, rawArtifactValidationRepository.findByRawArtifact_Id(artifact.id))
        }
    }

    @Transactional
    fun queue(sourceId: UUID): PipelineRunEntity {
        val source = dataSourceRepository.findById(sourceId).orElseThrow { notFound("Data source", sourceId) }
        return pipelineRunRepository.save(PipelineRunEntity(source = source))
    }

    @Transactional(readOnly = true)
    fun job(runId: UUID): IngestionJob {
        val run = run(runId)
        requireStatus(run, PipelineRunStatus.QUEUED)
        val source = run.source ?: throw notFound("Data source", runId)
        return IngestionJob(run.id, source.id, source.location, source.normalizer?.name)
    }

    @Transactional
    fun start(runId: UUID): PipelineRunEntity {
        val run = run(runId)
        requireStatus(run, PipelineRunStatus.QUEUED)
        run.status = PipelineRunStatus.RUNNING
        run.startedAt = Instant.now()
        return run
    }

    @Transactional
    fun complete(runId: UUID, request: CompleteRunRequest): PipelineRunEntity {
        val run = run(runId)
        requireStatus(run, PipelineRunStatus.RUNNING)
        val source = run.source ?: throw notFound("Data source", runId)
        require(request.payload.size.toLong() <= maxPayloadBytes) { "Payload exceeds the configured maximum size" }
        require(request.payload.size.toLong() == request.contentLength) { "Payload length does not match contentLength" }
        val calculatedChecksum = MessageDigest.getInstance("SHA-256").digest(request.payload).joinToString("") { "%02x".format(it.toInt() and 0xff) }
        require(calculatedChecksum.equals(request.checksumSha256, ignoreCase = true)) { "Payload checksum does not match checksumSha256" }
        val artifactId = UUID.randomUUID()
        val artifact = rawArtifactRepository.save(RawArtifactEntity(id = artifactId, pipelineRun = run, source = source, storageUri = "postgres://raw-artifacts/$artifactId", payload = request.payload, contentType = request.contentType, contentLength = request.contentLength, checksumSha256 = calculatedChecksum, sourceVersion = request.sourceVersion))
        request.validation?.let { validation ->
            rawArtifactValidationRepository.save(RawArtifactValidationEntity(rawArtifact = artifact, status = validation.status, detectedFormat = validation.detectedFormat, recordCount = validation.recordCount, schemaFingerprint = validation.schemaFingerprint, failureReason = validation.failureReason))
        }
        request.energyObservation?.let { observation -> energyCurationService.curate(artifact.id, observation) }
        run.status = PipelineRunStatus.SUCCEEDED
        run.completedAt = Instant.now()
        return run
    }

    @Transactional
    fun fail(runId: UUID, reason: String): PipelineRunEntity {
        val run = run(runId)
        if (run.status !in setOf(PipelineRunStatus.QUEUED, PipelineRunStatus.RUNNING)) throw invalidState(run)
        run.status = PipelineRunStatus.FAILED
        run.completedAt = Instant.now()
        run.failureReason = reason
        return run
    }

    @Transactional(readOnly = true)
    fun artifactContent(artifactId: UUID): RawArtifactEntity = rawArtifactRepository.findById(artifactId).orElseThrow { notFound("Raw artifact", artifactId) }

    private fun run(id: UUID) = pipelineRunRepository.findById(id).orElseThrow { notFound("Pipeline run", id) }
    private fun requireStatus(run: PipelineRunEntity, status: PipelineRunStatus) { if (run.status != status) throw invalidState(run) }
    private fun invalidState(run: PipelineRunEntity) = ResponseStatusException(HttpStatus.CONFLICT, "Pipeline run ${run.id} is ${run.status}")
    private fun notFound(type: String, id: UUID) = ResponseStatusException(HttpStatus.NOT_FOUND, "$type $id was not found")
}

data class IngestionJob(val runId: UUID, val sourceId: UUID, val location: String, val normalizer: String?)
data class RawArtifactWithValidation(val artifact: RawArtifactEntity, val validation: RawArtifactValidationEntity?)
