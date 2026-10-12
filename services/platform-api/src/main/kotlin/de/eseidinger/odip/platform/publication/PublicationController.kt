package de.eseidinger.odip.platform.publication

import jakarta.servlet.http.HttpServletRequest
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.scheduling.annotation.EnableScheduling
import org.springframework.context.annotation.Configuration
import org.springframework.web.bind.annotation.*
import java.util.UUID
import java.time.Instant
import org.springframework.transaction.annotation.Transactional

@Configuration
@EnableScheduling
class PublicationScheduling

@RestController
@RequestMapping("/api/v1")
class PublicationController(private val service: PublicationService, private val access: DatasetAccess, private val jdbc: JdbcTemplate) {
    @PutMapping("/publication-retention")
    @Transactional
    fun support(request: HttpServletRequest, @RequestBody body: SupportEndRequest): ResponseEntity<Void> {
        access.requireOperator(request)
        checkPublication(body.schemaRef.length in 1..200 && body.supportEndsAt.isAfter(Instant.now()),"invalid_retention","Support end must be in the future",400)
        jdbc.update("INSERT INTO publication_support VALUES (?,?) ON CONFLICT(schema_ref) DO UPDATE SET support_ends_at=EXCLUDED.support_ends_at",body.schemaRef,java.sql.Timestamp.from(body.supportEndsAt))
        access.audit(access.principal(request),"support_end_recorded")
        return ResponseEntity.noContent().build()
    }
    @GetMapping("/datasets")
    fun discover(request: HttpServletRequest, @RequestParam(required=false) schemaRef: String?, @RequestParam(defaultValue="PUBLISHED") status: String, @RequestParam(defaultValue="0") page: Int, @RequestParam(defaultValue="20") pageSize: Int): Map<String, Any> {
        checkPublication(status == "PUBLISHED", "invalid_status", "Only PUBLISHED discovery is supported", 400)
        return service.discover(request, schemaRef, page, pageSize)
    }

    @GetMapping("/datasets/{dataset}/versions/{version}")
    fun manifest(request: HttpServletRequest, @PathVariable dataset: String, @PathVariable version: String) = response(request, service.read(request, dataset, version, null))

    @GetMapping("/datasets/{dataset}/versions/{version}/artifacts/{artifact}")
    fun artifact(request: HttpServletRequest, @PathVariable dataset: String, @PathVariable version: String, @PathVariable artifact: String) = response(request, service.read(request, dataset, version, artifact))

    @GetMapping("/publication-drafts") fun drafts(request: HttpServletRequest) = service.drafts(request)
    @GetMapping("/publication-drafts/{id}") fun draft(request: HttpServletRequest, @PathVariable id: UUID) = service.draft(request, id)
    @PostMapping("/publication-drafts")
    fun create(request: HttpServletRequest, @RequestBody body: DraftRequest, @RequestHeader("Idempotency-Key") key: String) = ResponseEntity.status(201).body(service.create(request, body, key))
    @PutMapping("/publication-drafts/{id}/artifacts/{artifact}", consumes=["application/octet-stream"])
    fun upload(request: HttpServletRequest, @PathVariable id: UUID, @PathVariable artifact: String, @RequestBody bytes: ByteArray): ResponseEntity<Void> {
        service.upload(request, id, artifact, bytes)
        return ResponseEntity.noContent().build()
    }
    @GetMapping("/publication-drafts/{id}/artifacts/{artifact}")
    fun download(request: HttpServletRequest, @PathVariable id: UUID, @PathVariable artifact: String) = ResponseEntity.ok().contentType(MediaType.APPLICATION_OCTET_STREAM).body(service.operatorArtifact(request,id,artifact))
    @PostMapping("/publication-drafts/{id}/publish")
    fun publish(request: HttpServletRequest, @PathVariable id: UUID, @RequestHeader("Idempotency-Key") key: String) = ResponseEntity.accepted().body(service.publish(request, id, key))
    @PostMapping("/publication-jobs/claim-next")
    fun claim(request: HttpServletRequest): ResponseEntity<Map<String, Any?>> = service.claim(request)?.let { ResponseEntity.ok(it) } ?: ResponseEntity.noContent().build()
    @GetMapping("/publication-jobs/{id}/artifacts/{artifact}")
    fun input(request: HttpServletRequest, @PathVariable id: UUID, @PathVariable artifact: String) = ResponseEntity.ok().contentType(MediaType.APPLICATION_OCTET_STREAM).body(service.draftArtifact(request, id, artifact))
    @PostMapping("/publication-jobs/{id}/completed")
    fun complete(request: HttpServletRequest, @PathVariable id: UUID, @RequestBody report: ValidationReport) = service.complete(request, id, report)

    @GetMapping("/operator-capabilities")
    fun capabilities(request: HttpServletRequest) = mapOf("manageGrants" to access.operator(request), "writableDatasetIds" to
        jdbc.queryForList("SELECT id FROM dataset", UUID::class.java).filterNotNull().filter { access.allowed(access.principal(request),it,"WRITE") })
    @GetMapping("/dataset-grants/{dataset}")
    fun grants(request: HttpServletRequest, @PathVariable dataset: UUID): List<Map<String, Any?>> {
        access.requireOperator(request)
        return jdbc.queryForList("SELECT principal_id AS \"principalId\",permission FROM dataset_grant WHERE dataset_id=? ORDER BY principal_id,permission", dataset)
    }
    @PutMapping("/dataset-grants/{dataset}")
    @Transactional
    fun grant(request: HttpServletRequest, @PathVariable dataset: UUID, @RequestBody body: GrantRequest): ResponseEntity<Void> {
        access.requireOperator(request)
        checkPublication(jdbc.queryForList("SELECT id FROM dataset WHERE id=?", dataset).isNotEmpty(), "not_found", "Dataset was not found", 404)
        access.grant(dataset, body.principalId, body.permission)
        access.audit(access.principal(request), "grant_created", dataset)
        return ResponseEntity.noContent().build()
    }
    @DeleteMapping("/dataset-grants/{dataset}")
    @Transactional
    fun revoke(request: HttpServletRequest, @PathVariable dataset: UUID, @RequestParam principalId: String, @RequestParam permission: String): ResponseEntity<Void> {
        access.requireOperator(request)
        jdbc.update("DELETE FROM dataset_grant WHERE dataset_id=? AND principal_id=? AND permission=?", dataset, principalId, permission)
        access.audit(access.principal(request), "grant_revoked", dataset)
        return ResponseEntity.noContent().build()
    }

    private fun response(request: HttpServletRequest, data: Pair<ByteArray, String>): ResponseEntity<ByteArray> {
        val etag = "\"${sha256(data.first)}\""
        val supplied = request.getHeader("If-None-Match").orEmpty().split(',').map { it.trim().removePrefix("W/") }
        if (etag in supplied || "*" in supplied) return ResponseEntity.status(304).eTag(etag).build()
        return ResponseEntity.ok().eTag(etag).header("Cache-Control", "private, no-cache").contentType(MediaType.parseMediaType(data.second)).contentLength(data.first.size.toLong()).body(data.first)
    }
}

data class SupportEndRequest(val schemaRef: String, val supportEndsAt: Instant)
