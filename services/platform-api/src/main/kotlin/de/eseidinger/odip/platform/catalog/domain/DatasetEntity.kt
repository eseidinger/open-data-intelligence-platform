package de.eseidinger.odip.platform.catalog.domain

import jakarta.persistence.Column
import jakarta.persistence.Entity
import jakarta.persistence.EnumType
import jakarta.persistence.Enumerated
import jakarta.persistence.Id
import jakarta.persistence.JoinColumn
import jakarta.persistence.JoinTable
import jakarta.persistence.ManyToMany
import jakarta.persistence.PreUpdate
import jakarta.persistence.Table
import java.time.Instant
import java.util.UUID

@Entity
@Table(name = "dataset")
class DatasetEntity(
    @Id
    var id: UUID = UUID.randomUUID(),

    @Column(nullable = false, unique = true)
    var name: String = "",

    var description: String? = null,

    var owner: String? = null,

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    var classification: DatasetClassification = DatasetClassification.PUBLIC,

    @ManyToMany
    @JoinTable(
        name = "dataset_source",
        joinColumns = [JoinColumn(name = "dataset_id")],
        inverseJoinColumns = [JoinColumn(name = "source_id")],
    )
    var sources: MutableSet<DataSourceEntity> = linkedSetOf(),

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
