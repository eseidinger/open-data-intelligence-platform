package de.eseidinger.odip.platform.catalog.service

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import de.eseidinger.odip.platform.catalog.web.CreateDataSourceRequest
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.web.server.ResponseStatusException

@Service
class DataSourceService(
    private val dataSourceRepository: DataSourceRepository,
) {
    fun list(): List<DataSourceEntity> = dataSourceRepository.findAllByOrderByNameAsc()

    fun create(request: CreateDataSourceRequest): DataSourceEntity {
        if (dataSourceRepository.existsByName(request.name)) {
            throw ResponseStatusException(HttpStatus.CONFLICT, "A data source named '${request.name}' already exists")
        }

        return dataSourceRepository.save(
            DataSourceEntity(
                name = request.name,
                sourceType = request.sourceType,
                location = request.location,
                owner = request.owner?.ifBlank { null },
                license = request.license?.ifBlank { null },
                refreshCadence = request.refreshCadence?.ifBlank { null },
                normalizer = request.normalizer,
            ),
        )
    }
}
