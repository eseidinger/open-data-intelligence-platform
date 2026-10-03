package de.eseidinger.odip.platform.ingestion.domain

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.FetchType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.OneToOne
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "raw_artifact")
class RawArtifactEntity(
    @Id var id: UUID = UUID.randomUUID(),
    @OneToOne(fetch = FetchType.LAZY) @JoinColumn(name = "pipeline_run_id", nullable = false) var pipelineRun: PipelineRunEntity? = null,
    @ManyToOne(fetch = FetchType.LAZY) @JoinColumn(name = "source_id", nullable = false) var source: DataSourceEntity? = null,
    @Column(name = "storage_uri", nullable = false) var storageUri: String = "",
    @Column(name = "content_type") var contentType: String? = null,
    @Column(name = "content_length", nullable = false) var contentLength: Long = 0,
    @Column(name = "checksum_sha256", nullable = false) var checksumSha256: String = "",
    @Column(name = "source_version") var sourceVersion: String? = null,
    @Column(name = "retrieved_at", nullable = false) var retrievedAt: Instant = Instant.now(),
)
