package de.eseidinger.odip.platform.catalog.persistence

import de.eseidinger.odip.platform.catalog.domain.DatasetVersionEntity
import java.util.UUID
import org.springframework.data.jpa.repository.EntityGraph
import org.springframework.data.jpa.repository.JpaRepository

interface DatasetVersionRepository : JpaRepository<DatasetVersionEntity, UUID> {
    fun findByDataset_IdAndRawArtifact_Id(datasetId: UUID, rawArtifactId: UUID): DatasetVersionEntity?
    fun findFirstByDataset_IdOrderByVersionNumberDesc(datasetId: UUID): DatasetVersionEntity?
    @EntityGraph(attributePaths = ["rawArtifact"])
    fun findAllByDataset_IdOrderByVersionNumberDesc(datasetId: UUID): List<DatasetVersionEntity>
}
