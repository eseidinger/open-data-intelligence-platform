package de.eseidinger.odip.platform.ingestion.domain

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.FetchType
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.OneToOne
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "raw_artifact_validation")
class RawArtifactValidationEntity(
    @Id var id: UUID = UUID.randomUUID(),
    @OneToOne(fetch = FetchType.LAZY) @JoinColumn(name = "raw_artifact_id", nullable = false) var rawArtifact: RawArtifactEntity? = null,
    @Enumerated(EnumType.STRING) @Column(nullable = false) var status: ArtifactValidationStatus = ArtifactValidationStatus.UNSUPPORTED,
    @Column(name = "detected_format") var detectedFormat: String? = null,
    @Column(name = "record_count") var recordCount: Long? = null,
    @Column(name = "schema_fingerprint") var schemaFingerprint: String? = null,
    @Column(name = "failure_reason") var failureReason: String? = null,
    @Column(name = "validated_at", nullable = false) var validatedAt: Instant = Instant.now(),
)
