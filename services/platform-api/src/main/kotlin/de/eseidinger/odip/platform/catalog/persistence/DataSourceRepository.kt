package de.eseidinger.odip.platform.catalog.persistence

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import org.springframework.data.jpa.repository.JpaRepository
import java.util.UUID

interface DataSourceRepository : JpaRepository<DataSourceEntity, UUID> {
    fun existsByName(name: String): Boolean

    fun findAllByOrderByNameAsc(): List<DataSourceEntity>
}
