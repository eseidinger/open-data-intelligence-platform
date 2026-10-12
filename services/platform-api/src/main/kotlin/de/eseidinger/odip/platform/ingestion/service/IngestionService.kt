package de.eseidinger.odip.platform.ingestion.service

import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
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
import de.eseidinger.odip.platform.publication.DatasetAccess
import de.eseidinger.odip.platform.publication.checkPublication
import jakarta.servlet.http.HttpServletRequest
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.scheduling.annotation.Scheduled

@Service
class IngestionService(
    private val dataSourceRepository: DataSourceRepository,
    private val pipelineRunRepository: PipelineRunRepository,
    private val rawArtifactRepository: RawArtifactRepository,
    private val rawArtifactValidationRepository: RawArtifactValidationRepository,
    private val transformations: List<ArtifactTransformation>,
    private val access: DatasetAccess,
    private val request: HttpServletRequest,
    private val jdbc: JdbcTemplate,
    @Value("\${odip.raw-artifact.max-payload-bytes}") private val maxPayloadBytes: Long,
) {
    @Transactional(readOnly = true)
    fun list(): List<PipelineRunEntity> = pipelineRunRepository.findAll().filter { it.source?.let { source -> sourceAllowed(source.id) } == true }.sortedByDescending { it.requestedAt }

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

    /** Claims the oldest queued run and moves it to RUNNING in one transaction. */
    @Transactional
    fun claimNext(): IngestionJob? {
        val principal = access.principal(request)
        val run = pipelineRunRepository.claimNextQueued(principal, access.operator(request)) ?: return null
        val source = run.source ?: throw notFound("Data source", run.id)
        run.status = PipelineRunStatus.RUNNING
        run.startedAt = Instant.now()
        run.ownerPrincipal = principal
        run.claimToken = UUID.randomUUID()
        return IngestionJob(run.id, source.id, source.location, source.normalizer, run.claimToken)
    }

    @Transactional(readOnly = true)
    fun job(runId: UUID): IngestionJob {
        val run = run(runId)
        requireStatus(run, PipelineRunStatus.QUEUED)
        val source = run.source ?: throw notFound("Data source", runId)
        return IngestionJob(run.id, source.id, source.location, source.normalizer)
    }

    @Transactional
    fun start(runId: UUID): PipelineRunEntity {
        val run = run(runId,true)
        requireStatus(run, PipelineRunStatus.QUEUED)
        run.status = PipelineRunStatus.RUNNING
        run.startedAt = Instant.now()
        run.ownerPrincipal = access.principal(request)
        run.claimToken = UUID.randomUUID()
        return run
    }

    @Transactional
    fun complete(runId: UUID, request: CompleteRunRequest): PipelineRunEntity {
        val run = run(runId,true)
        checkPublication(run.ownerPrincipal == access.principal(this.request), "forbidden", "Only the owning worker may complete the run", 403)
        checkPublication(access.operator(this.request) || request.claimToken != null && request.claimToken == run.claimToken, "stale_claim", "The ingestion claim is no longer current", 409)
        if (run.status == PipelineRunStatus.SUCCEEDED) {
            val prior = rawArtifactRepository.findAllByPipelineRun_IdOrderByRetrievedAtDesc(runId).singleOrNull()
            checkPublication(prior?.checksumSha256 == request.checksumSha256.lowercase() && prior?.payload?.contentEquals(request.payload) == true, "completion_conflict", "Run already completed with different content", 409)
            return run
        }
        requireStatus(run, PipelineRunStatus.RUNNING)
        val source = run.source ?: throw notFound("Data source", runId)
        checkPublication(request.payload.size.toLong() <= maxPayloadBytes, "payload_too_large", "Payload exceeds the configured maximum size", 413)
        checkPublication(request.payload.size.toLong() == request.contentLength, "invalid_length", "Payload length does not match contentLength", 400)
        val calculatedChecksum = MessageDigest.getInstance("SHA-256").digest(request.payload).joinToString("") { "%02x".format(it.toInt() and 0xff) }
        checkPublication(calculatedChecksum.equals(request.checksumSha256, ignoreCase = true), "checksum_mismatch", "Payload checksum does not match checksumSha256", 400)
        val artifactId = UUID.randomUUID()
        val artifact = rawArtifactRepository.save(RawArtifactEntity(id = artifactId, pipelineRun = run, source = source, storageUri = "postgres://raw-artifacts/$artifactId", payload = request.payload, contentType = request.contentType, contentLength = request.contentLength, checksumSha256 = calculatedChecksum, sourceVersion = request.sourceVersion))
        request.validation?.let { validation ->
            rawArtifactValidationRepository.save(RawArtifactValidationEntity(rawArtifact = artifact, status = validation.status, detectedFormat = validation.detectedFormat, recordCount = validation.recordCount, schemaFingerprint = validation.schemaFingerprint, failureReason = validation.failureReason))
        }
        request.transformation?.let { transformation ->
            val adapter = transformations.singleOrNull { it.id == transformation.id }
                ?: throw ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, "Unsupported transformation")
            adapter.apply(artifact.id, transformation.data)
        }
        run.status = PipelineRunStatus.SUCCEEDED
        run.completedAt = Instant.now()
        return run
    }

    @Transactional
    fun fail(runId: UUID, reason: String): PipelineRunEntity {
        val run = run(runId,true)
        checkPublication(run.ownerPrincipal == access.principal(request) || run.status == PipelineRunStatus.QUEUED && access.operator(request), "forbidden", "Only the owning worker may fail the run", 403)
        if (run.status !in setOf(PipelineRunStatus.QUEUED, PipelineRunStatus.RUNNING)) throw invalidState(run)
        run.status = PipelineRunStatus.FAILED
        run.completedAt = Instant.now()
        run.failureReason = reason
        return run
    }

    @Transactional(readOnly = true)
    fun artifactContent(artifactId: UUID): RawArtifactEntity = rawArtifactRepository.findById(artifactId).orElseThrow { notFound("Raw artifact", artifactId) }

    private fun run(id: UUID, lock: Boolean = false): PipelineRunEntity =
        if (lock) pipelineRunRepository.locked(id) ?: throw notFound("Pipeline run",id)
        else pipelineRunRepository.findById(id).orElseThrow { notFound("Pipeline run", id) }
    private fun requireStatus(run: PipelineRunEntity, status: PipelineRunStatus) { if (run.status != status) throw invalidState(run) }
    private fun invalidState(run: PipelineRunEntity) = ResponseStatusException(HttpStatus.CONFLICT, "Pipeline run ${run.id} is ${run.status}")
    private fun notFound(type: String, id: UUID) = ResponseStatusException(HttpStatus.NOT_FOUND, "$type $id was not found")

    private fun sourceAllowed(source: UUID): Boolean = jdbc.queryForList("SELECT dataset_id FROM dataset_source WHERE source_id=?", UUID::class.java, source)
        .filterNotNull().any { access.allowed(access.principal(request), it, "READ") } || access.operator(request)

    @Scheduled(fixedDelay = 60000)
    @Transactional
    fun recoverAbandoned() {
        jdbc.update("UPDATE pipeline_run SET status='FAILED',failure_reason='worker_timeout',completed_at=CURRENT_TIMESTAMP WHERE status='RUNNING' AND started_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes'")
    }
}

data class IngestionJob(val runId: UUID, val sourceId: UUID, val location: String, val normalizer: String?, val claimToken: UUID? = null)
data class RawArtifactWithValidation(val artifact: RawArtifactEntity, val validation: RawArtifactValidationEntity?)
