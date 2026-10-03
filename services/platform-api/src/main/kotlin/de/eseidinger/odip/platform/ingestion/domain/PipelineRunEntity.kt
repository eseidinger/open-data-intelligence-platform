package de.eseidinger.odip.platform.ingestion.domain

import de.eseidinger.odip.platform.catalog.domain.DataSourceEntity
import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.FetchType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.ManyToOne
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "pipeline_run")
class PipelineRunEntity(
    @Id var id: UUID = UUID.randomUUID(),
    @Column(name = "pipeline_name", nullable = false) var pipelineName: String = "raw-ingestion",
    @ManyToOne(fetch = FetchType.EAGER) @JoinColumn(name = "source_id") var source: DataSourceEntity? = null,
    @Enumerated(EnumType.STRING) @Column(nullable = false) var status: PipelineRunStatus = PipelineRunStatus.QUEUED,
    @Column(name = "requested_at", nullable = false) var requestedAt: Instant = Instant.now(),
    @Column(name = "started_at") var startedAt: Instant? = null,
    @Column(name = "completed_at") var completedAt: Instant? = null,
    @Column(name = "failure_reason") var failureReason: String? = null,
)
