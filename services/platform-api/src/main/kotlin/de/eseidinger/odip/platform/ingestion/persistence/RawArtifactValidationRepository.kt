package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.RawArtifactValidationEntity
import java.util.UUID
import org.springframework.data.jpa.repository.JpaRepository

interface RawArtifactValidationRepository : JpaRepository<RawArtifactValidationEntity, UUID> {
    fun findByRawArtifact_Id(rawArtifactId: UUID): RawArtifactValidationEntity?
}
