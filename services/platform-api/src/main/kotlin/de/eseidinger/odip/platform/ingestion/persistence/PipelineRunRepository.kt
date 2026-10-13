package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import java.util.UUID
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import org.springframework.data.jpa.repository.Lock
import jakarta.persistence.LockModeType

interface PipelineRunRepository : JpaRepository<PipelineRunEntity, UUID> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT r FROM PipelineRunEntity r WHERE r.id=:id")
    fun locked(id: UUID): PipelineRunEntity?
    @Query(value = "SELECT * FROM pipeline_run r WHERE status = 'QUEUED' AND (:developmentBypass OR EXISTS(SELECT 1 FROM dataset_source ds JOIN dataset_grant g ON ds.dataset_id=g.dataset_id WHERE ds.source_id=r.source_id AND g.principal_id=:principal AND g.permission='INGEST')) ORDER BY requested_at FOR UPDATE SKIP LOCKED LIMIT 1", nativeQuery = true)
    fun claimNextQueued(principal: String, developmentBypass: Boolean): PipelineRunEntity?
}
