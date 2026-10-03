package de.eseidinger.odip.platform.catalog.domain

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.PreUpdate
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "data_source")
class DataSourceEntity(
    @Id
    var id: UUID = UUID.randomUUID(),

    @Column(nullable = false, unique = true)
    var name: String = "",

    @Enumerated(EnumType.STRING)
    @Column(name = "source_type", nullable = false)
    var sourceType: DataSourceType = DataSourceType.API,

    @Column(nullable = false)
    var location: String = "",

    var owner: String? = null,

    var license: String? = null,

    @Column(name = "refresh_cadence")
    var refreshCadence: String? = null,

    @Column(name = "created_at", nullable = false, updatable = false)
    var createdAt: Instant = Instant.now(),

    @Column(name = "updated_at", nullable = false)
    var updatedAt: Instant = Instant.now(),
) {
    @PreUpdate
    fun updateTimestamp() {
        updatedAt = Instant.now()
    }
}
