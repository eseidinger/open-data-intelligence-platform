package de.eseidinger.odip.platform

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class PlatformApiApplication

fun main(args: Array<String>) {
	runApplication<PlatformApiApplication>(*args)
}
