package de.eseidinger.odip.platform.catalog.domain

import de.eseidinger.odip.platform.ingestion.domain.RawArtifactEntity
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.FetchType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.Table
import org.hibernate.annotations.JdbcTypeCode
import org.hibernate.type.SqlTypes
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "dataset_version")
class DatasetVersionEntity(
    @Id var id: UUID = UUID.randomUUID(),
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "dataset_id", nullable = false) var dataset: DatasetEntity? = null,
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "raw_artifact_id") var rawArtifact: RawArtifactEntity? = null,
    @Column(name = "version_number", nullable = false) var versionNumber: Long = 0,
    @Column(nullable = false) var status: String = "PUBLISHED",
    @JdbcTypeCode(SqlTypes.JSON) @Column(name = "schema_definition", nullable = false, columnDefinition = "jsonb") var schemaDefinition: Map<String, Any?> = emptyMap(),
    @JdbcTypeCode(SqlTypes.JSON) @Column(name = "quality_summary", nullable = false, columnDefinition = "jsonb") var qualitySummary: Map<String, Any?> = emptyMap(),
    @Column(name = "created_at", nullable = false) var createdAt: Instant = Instant.now(),
)
