package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.RawArtifactValidationEntity
import org.springframework.data.jpa.repository.JpaRepository
import java.util.UUID

// Spring Data uses underscores to disambiguate nested property traversal.
@Suppress("ktlint:standard:function-naming")
interface RawArtifactValidationRepository : JpaRepository<RawArtifactValidationEntity, UUID> {
    fun findByRawArtifact_Id(rawArtifactId: UUID): RawArtifactValidationEntity?
}
