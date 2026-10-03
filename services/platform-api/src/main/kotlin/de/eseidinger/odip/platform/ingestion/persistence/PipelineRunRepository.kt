package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.PipelineRunEntity
import java.util.UUID
import org.springframework.data.jpa.repository.JpaRepository

interface PipelineRunRepository : JpaRepository<PipelineRunEntity, UUID>
