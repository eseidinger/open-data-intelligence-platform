package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import java.util.UUID
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query

interface PipelineRunRepository : JpaRepository<PipelineRunEntity, UUID> {
    @Query(value = "SELECT * FROM pipeline_run WHERE status = 'QUEUED' ORDER BY requested_at FOR UPDATE SKIP LOCKED LIMIT 1", nativeQuery = true)
    fun claimNextQueued(): PipelineRunEntity?
}
