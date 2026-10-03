package de.eseidinger.odip.platform.catalog.service

import de.eseidinger.odip.platform.catalog.domain.DatasetVersionEntity
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.catalog.persistence.DatasetVersionRepository
import java.util.UUID
import org.springframework.http.HttpStatus
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import org.springframework.web.server.ResponseStatusException

@Service
class DatasetVersionService(
    private val datasets: DatasetRepository,
    private val versions: DatasetVersionRepository,
) {
    @Transactional(readOnly = true)
    fun list(datasetId: UUID): List<DatasetVersionEntity> {
        if (!datasets.existsById(datasetId)) throw ResponseStatusException(HttpStatus.NOT_FOUND, "Dataset $datasetId was not found")
        return versions.findAllByDataset_IdOrderByVersionNumberDesc(datasetId)
    }
}
