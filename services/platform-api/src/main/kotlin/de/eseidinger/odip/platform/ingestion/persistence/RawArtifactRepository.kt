package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import org.springframework.data.jpa.repository.JpaRepository
import java.util.UUID

// Spring Data uses underscores to disambiguate nested property traversal.
@Suppress("ktlint:standard:function-naming")
interface RawArtifactRepository : JpaRepository<RawArtifactEntity, UUID> {
    fun findAllByPipelineRun_IdOrderByRetrievedAtDesc(pipelineRunId: UUID): List<RawArtifactEntity>
}
