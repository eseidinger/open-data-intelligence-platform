package de.eseidinger.odip.platform.catalog.persistence

import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import java.util.UUID
import org.springframework.data.jpa.repository.EntityGraph
import org.springframework.data.jpa.repository.JpaRepository

interface DatasetRepository : JpaRepository<DatasetEntity, UUID> {
    fun existsByName(name: String): Boolean
    fun findAllBySources_Id(sourceId: UUID): List<DatasetEntity>

    @EntityGraph(attributePaths = ["sources"])
    fun findAllByOrderByNameAsc(): List<DatasetEntity>
}
