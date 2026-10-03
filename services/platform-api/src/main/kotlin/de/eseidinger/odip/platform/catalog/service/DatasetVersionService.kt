package de.eseidinger.odip.platform.catalog.service

import de.eseidinger.odip.platform.catalog.domain.DatasetVersionEntity
import de.eseidinger.odip.platform.catalog.persistence.DatasetRepository
import de.eseidinger.odip.platform.catalog.persistence.DatasetVersionRepository
import java.util.UUID
import java.time.Instant
import java.time.temporal.ChronoUnit
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

    @Transactional(readOnly = true)
    fun summary(datasetId: UUID): DatasetSummary {
        if (!datasets.existsById(datasetId)) throw ResponseStatusException(HttpStatus.NOT_FOUND, "Dataset $datasetId was not found")
        val version = versions.findFirstByDataset_IdOrderByVersionNumberDesc(datasetId)
            ?: return DatasetSummary(datasetId, null, null, "UNKNOWN", null, "NOT_RECORDED", null)
        val artifact = version.rawArtifact
            ?: return DatasetSummary(datasetId, version.versionNumber, null, "UNKNOWN", null, qualityStatus(version), recordCount(version))
        val dueAt = cadenceDuration(artifact.source?.refreshCadence)?.let { artifact.retrievedAt.plus(it.first, it.second) }
        val freshness = when {
            dueAt == null -> "UNKNOWN"
            dueAt.isBefore(Instant.now()) -> "STALE"
            else -> "FRESH"
        }
        return DatasetSummary(datasetId, version.versionNumber, artifact.retrievedAt, freshness, dueAt, qualityStatus(version), recordCount(version))
    }

    private fun cadenceDuration(cadence: String?) = when (cadence?.lowercase()) {
        "daily" -> 1L to ChronoUnit.DAYS
        "weekly" -> 7L to ChronoUnit.DAYS
        "monthly" -> 30L to ChronoUnit.DAYS
        "annual", "yearly" -> 365L to ChronoUnit.DAYS
        else -> null
    }

    private fun qualityStatus(version: DatasetVersionEntity) = version.qualitySummary["validationStatus"] as? String ?: "NOT_RECORDED"
    private fun recordCount(version: DatasetVersionEntity) = (version.qualitySummary["recordCount"] as? Number)?.toLong()
}

data class DatasetSummary(val datasetId: UUID, val latestVersionNumber: Long?, val retrievedAt: Instant?, val freshnessStatus: String, val freshnessDueAt: Instant?, val validationStatus: String, val recordCount: Long?)
