package de.eseidinger.odip.platform.catalog.persistence

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import java.util.UUID
import org.springframework.data.jpa.repository.JpaRepository

interface DataSourceRepository : JpaRepository<DataSourceEntity, UUID> {
    fun existsByName(name: String): Boolean

    fun findAllByOrderByNameAsc(): List<DataSourceEntity>
}
