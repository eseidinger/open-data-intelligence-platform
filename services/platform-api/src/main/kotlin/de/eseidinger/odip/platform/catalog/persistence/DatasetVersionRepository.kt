package de.eseidinger.odip.platform.catalog.persistence

import de.eseidinger.odip.platform.catalog.domain.DatasetVersionEntity
import org.springframework.data.jpa.repository.EntityGraph
import org.springframework.data.jpa.repository.JpaRepository
import java.util.UUID

// Spring Data uses underscores to disambiguate nested property traversal.
@Suppress("ktlint:standard:function-naming")
interface DatasetVersionRepository : JpaRepository<DatasetVersionEntity, UUID> {
    fun findByDataset_IdAndRawArtifact_Id(datasetId: UUID, rawArtifactId: UUID): DatasetVersionEntity?

    @EntityGraph(attributePaths = ["rawArtifact", "rawArtifact.source"])
    fun findAllByDataset_IdOrderByVersionNumberDesc(datasetId: UUID): List<DatasetVersionEntity>

    @EntityGraph(attributePaths = ["rawArtifact", "rawArtifact.source"])
    fun findFirstByDataset_IdOrderByVersionNumberDesc(datasetId: UUID): DatasetVersionEntity?
}
