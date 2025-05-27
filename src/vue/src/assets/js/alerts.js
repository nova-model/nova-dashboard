const envs = import.meta.env.VITE_ALERTS_ENVIRONMENTS
const format = import.meta.env.VITE_ALERTS_FORMAT
const url = import.meta.env.VITE_ALERTS_URL

function processPrometheus(rawData) {
    const alerts = []

    const prometheusData = rawData?.data?.alerts || []
    for (const alert of prometheusData) {
        alerts.push({
            environment: alert?.labels?.env,
            subtitle: alert?.annotations?.description,
            title: alert?.annotations?.title
        })
    }

    return alerts
}

export default async function getAlertData() {
    const response = await fetch(url)
    const rawData = await response.json()

    // Create a standard alert object from the raw alert format
    let processedData
    if (format === "prometheus") {
        processedData = processPrometheus(rawData)
    } else {
        throw TypeError(`Status format "${format}" is not implemented.`)
    }

    // Only show alerts from selected environments
    const alertData = []
    for (const alert of processedData) {
        if (envs.includes(alert.environment)) {
            alertData.push(alert)
        }
    }

    return alertData
}
