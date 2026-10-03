package de.eseidinger.odip.platform.ingestion.domain

enum class PipelineRunStatus {
    QUEUED,
    RUNNING,
    SUCCEEDED,
    FAILED,
}
