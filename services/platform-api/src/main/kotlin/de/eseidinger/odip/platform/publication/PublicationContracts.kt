package de.eseidinger.odip.platform.publication

import com.fasterxml.jackson.core.JsonParser
import com.fasterxml.jackson.databind.JsonNode
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.databind.node.ObjectNode
import com.networknt.schema.JsonSchemaFactory
import com.networknt.schema.SpecVersion
import org.erdtman.jcs.JsonCanonicalizer
import org.springframework.core.io.support.PathMatchingResourcePatternResolver
import org.springframework.stereotype.Component
import java.security.MessageDigest

class PublicationError(val status: Int, val code: String, override val message: String) : RuntimeException(message)
fun reject(status: Int, code: String, message: String): Nothing = throw PublicationError(status, code, message)
fun checkPublication(condition: Boolean, code: String, message: String, status: Int = 422) {
    if (!condition) reject(status, code, message)
}
fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }

@Component
class PublicationContracts {
    val mapper = ObjectMapper().enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION).enable(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
    private val definitions = PathMatchingResourcePatternResolver().getResources("classpath*:contract-schemas/*.schema.json")
        .associate { resource -> resource.filename!!.removeSuffix(".schema.json") to mapper.readTree(resource.inputStream) }
    private val namesById = definitions.map { (name, node) -> node.path("\$id").asText() to name }.toMap()
    private val factory = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012)
    private val compiled = definitions.keys.associateWith { name ->
        val root = mapper.createObjectNode()
        root.put("\$schema", "https://json-schema.org/draft/2020-12/schema")
        root.put("\$ref", "#/\$defs/schemas/$name")
        val schemas = root.putObject("\$defs").putObject("schemas")
        definitions.forEach { (key, value) -> schemas.set<JsonNode>(key, rewrite(value, key)) }
        factory.getSchema(root)
    }
    val policies: JsonNode = mapper.readTree(javaClass.getResourceAsStream("/publication-policies.json"))

    private fun rewrite(node: JsonNode, context: String): JsonNode {
        if (node.isArray) return mapper.createArrayNode().also { array -> node.forEach { array.add(rewrite(it, context)) } }
        if (!node.isObject) return node
        val result = mapper.createObjectNode()
        node.fields().forEachRemaining { (key, value) ->
            if (key != "\$id") {
                if (key == "\$ref") {
                    val ref = value.asText()
                    val parts = ref.split('#', limit = 2)
                    val target = if (parts[0].isEmpty()) context else namesById[parts[0]] ?: error("Unregistered schema reference")
                    result.put(key, "#/\$defs/schemas/$target" + if (parts.size == 2) parts[1] else "")
                } else result.set<JsonNode>(key, rewrite(value, context))
            }
        }
        return result
    }

    fun parse(bytes: ByteArray): JsonNode = try {
        mapper.readTree(bytes) ?: reject(400, "invalid_json", "A JSON object is required")
    } catch (error: PublicationError) { throw error
    } catch (_: Exception) { reject(400, "invalid_json", "Malformed JSON, duplicate keys, or invalid numeric value") }

    fun canonical(bytes: ByteArray): ByteArray = try {
        parse(bytes)
        JsonCanonicalizer(bytes).encodedUTF8
    } catch (error: PublicationError) { throw error
    } catch (_: Exception) { reject(400, "invalid_json", "JSON cannot be represented by RFC 8785") }

    fun validate(name: String, document: JsonNode) {
        val errors = compiled[name]?.validate(document) ?: reject(422, "unsupported_schema", "Schema is not registered")
        checkPublication(errors.isEmpty(), "schema_validation_failed", "Document fails schema $name")
    }

    fun policy(manifest: JsonNode): JsonNode {
        val policy = policies[manifest.path("schemaRef").asText()] ?: reject(422, "unsupported_schema", "Publication schema is not supported")
        checkPublication(policy["policyRef"].asText() == manifest.path("quality").path("policyRef").asText(), "unsupported_policy", "Quality policy does not match the registered profile")
        return policy
    }
}
