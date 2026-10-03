package de.eseidinger.odip.platform.curation.domain

import de.eseidinger.odip.platform.catalog.domain.DatasetEntity
import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.FetchType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.Table
import java.math.BigDecimal
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "energy_observation")
class EnergyObservationEntity(
    @Id var id: UUID = UUID.randomUUID(),
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "raw_artifact_id", nullable = false) var rawArtifact: RawArtifactEntity? = null,
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "dataset_id", nullable = false) var dataset: DatasetEntity? = null,
    @Column(name = "indicator_code", nullable = false) var indicatorCode: String = "",
    @Column(name = "geo_code", nullable = false) var geoCode: String = "",
    @Column(name = "observation_year", nullable = false) var observationYear: Int = 0,
    @Column(name = "unit_code", nullable = false) var unitCode: String = "",
    @Column(name = "observation_value", nullable = false) var observationValue: BigDecimal = BigDecimal.ZERO,
    @Column(name = "created_at", nullable = false) var createdAt: Instant = Instant.now(),
)
