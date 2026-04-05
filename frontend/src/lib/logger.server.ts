import { env } from '$env/dynamic/private'
import winston from 'winston'
import LokiTransport from 'winston-loki'

const transports: winston.transport[] = [
	new winston.transports.Console({
		format: winston.format.combine(winston.format.timestamp(), winston.format.simple())
	})
]

// Add Custom Logger (Loki) transport if CUSTOM_LOGGER_URL is configured
if (env.CUSTOM_LOGGER_URL) {
	transports.push(
		new LokiTransport({
			host: env.CUSTOM_LOGGER_URL,
			labels: {
				app: 'comparag-frontend',
				environment: env.ENVIR || 'dev'
			},
			json: true,
			format: winston.format.json(),
			replaceTimestamp: true,
			onConnectionError: (err) => console.error('Custom Logger connection error:', err)
		})
	)
}

export const logger = winston.createLogger({
	level: env.LANGUIA_DEBUG === 'true' ? 'debug' : 'info',
	format: winston.format.combine(
		winston.format.timestamp(),
		winston.format.errors({ stack: true }),
		winston.format.json()
	),
	transports
})
