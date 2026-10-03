package de.eseidinger.odip.platform.ingestion.persistence

import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import java.util.UUID
import org.springframework.data.jpa.repository.JpaRepository

interface RawArtifactRepository : JpaRepository<RawArtifactEntity, UUID>
