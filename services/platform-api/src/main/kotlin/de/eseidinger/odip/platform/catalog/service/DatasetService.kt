package de.eseidinger.odip.platform.catalog.service

import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.catalog.persistence.DataSourceRepository
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.catalog.web.CreateDatasetRequest
import de.eseidinger.odip.platform.publication.DatasetAccess
import jakarta.servlet.http.HttpServletRequest
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.server.ResponseStatusException

@Service
class DatasetService(
    private val datasetRepository: DatasetRepository,
    private val dataSourceRepository: DataSourceRepository,
    private val access: DatasetAccess,
    private val httpRequest: HttpServletRequest,
) {
    @Transactional(readOnly = true)
    fun list(): List<DatasetEntity> = datasetRepository.findAllByOrderByNameAsc().filter { access.allowed(access.principal(httpRequest), it.id, "READ") }

    @Transactional
    fun create(request: CreateDatasetRequest): DatasetEntity {
        // Dataset registration is protected by the platform's operator route.
        if (datasetRepository.existsByName(request.name)) {
            throw ResponseStatusException(HttpStatus.CONFLICT, "A dataset named '${request.name}' already exists")
        }

        val uniqueSourceIds = request.sourceIds.toSet()
        if (uniqueSourceIds.size != request.sourceIds.size) {
            throw ResponseStatusException(HttpStatus.BAD_REQUEST, "Each source can be linked only once")
        }

        val sources = dataSourceRepository.findAllById(uniqueSourceIds)
        if (sources.size != uniqueSourceIds.size) {
            throw ResponseStatusException(HttpStatus.BAD_REQUEST, "One or more source IDs are not registered")
        }

        val dataset = datasetRepository.saveAndFlush(
            DatasetEntity(
                name = request.name,
                description = request.description?.ifBlank { null },
                owner = request.owner?.ifBlank { null },
                classification = request.classification,
                sources = sources.toMutableSet(),
            ),
        )
        listOf("READ", "WRITE", "INGEST", "VALIDATE").forEach { access.grant(dataset.id, access.principal(httpRequest), it) }
        return dataset
    }
}
