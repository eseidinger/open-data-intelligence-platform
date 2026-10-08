package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import jakarta.persistence.LockModeType
import java.util.UUID
import org.springframework.data.jpa.repository.Lock
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query

interface PipelineRunRepository : JpaRepository<PipelineRunEntity, UUID> {
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query(value = "SELECT * FROM pipeline_run WHERE status = 'QUEUED' ORDER BY requested_at FOR UPDATE SKIP LOCKED LIMIT 1", nativeQuery = true)
    fun claimNextQueued(): PipelineRunEntity?
}
