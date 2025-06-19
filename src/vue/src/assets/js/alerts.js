// Tracks the status of an individual alert alias.
class Alias {
    constructor(name) {
        this.name = name
        this.status = "success"
    }

    reset() {
        this.status = "success"
    }

    setStatus(alert) {
        if (alert.severity === "critical") {
            this.status = alert.severity
        } else if (alert.severity === "warning" && this.status !== "critical") {
            this.status = alert.severity
        }
    }
}

// Tracks the status of a service.
class Service {
    constructor(name, aliases) {
        if (aliases === undefined) {
            aliases = []
        }

        this.alerts = []
        this.aliases = aliases.sort((a, b) => a.name.localeCompare(b.name))
        this.countText = ""
        this.name = name
        this.status = "success"
    }

    reset() {
        this.alerts = []
        this.countText = ""
        this.status = "success"
    }

    addAlert(alert) {
        this.alerts.push(alert)

        for (const alias of this.aliases) {
            if (alias.name === alert.alias) {
                alias.setStatus(alert)
            }
        }
    }

    update() {
        this.updateCountText()
        this.updateStatus()
    }

    updateCountText() {
        if (this.aliases.length === 0) {
            this.countText = ""
        } else {
            this.countText = ` (${this.aliases.length - this.alerts.length} of ${this.aliases.length} up)`
        }
    }

    updateStatus() {
        if (this.alerts.some((alert) => alert?.severity === "critical")) {
            this.status = "critical"
        } else if (this.alerts.some((alert) => alert?.severity === "warning")) {
            this.status = "warning"
        } else {
            this.status = "success"
        }
    }
}

// API class, this is responsible for interacting with the alert monitoring endpoint and triggering relevant state updates.
export default class AlertManager {
    constructor() {
        this.alertsUrl = "/api/status/alerts/"
        this.targetsUrl = "/api/status/targets/"

        this.alerts = []
        this.services = null
        this.monitoringUrl = ""
    }

    reset() {
        this.alerts = []
        for (const key in this.services) {
            this.services[key].reset()
        }
    }

    async initServices() {
        this.services = {
            infrastructure: new Service("Infrastructure"),
            compute: new Service("Compute Resources", await this.getAliases("compute")),
            live_data: new Service("Live Data"),
            documentation: new Service("Documentation")
        }
    }

    async getAliases(key) {
        const response = await fetch(this.targetsUrl)
        const targets = await response.json()

        const aliases = {}
        for (const target of targets) {
            if (target.group === key) {
                aliases[target.alias] = new Alias(target.alias)
            }
        }

        return Object.values(aliases)
    }

    getStatus() {
        if (this.alerts.some((alert) => alert?.severity === "critical")) {
            return "critical"
        }

        if (this.alerts.some((alert) => alert?.severity === "warning")) {
            return "warning"
        }

        return "success"
    }

    async update() {
        if (this.services === null) {
            await this.initServices()
        }

        const response = await fetch(this.alertsUrl)
        const data = await response.json()
        this.monitoringUrl = data?.url

        this.reset()

        const alerts = data?.alerts || []
        for (const alert of alerts) {
            if (alert.group in this.services) {
                this.alerts.push(alert)
                this.services[alert.group].addAlert(alert)
            }
        }

        for (const key in this.services) {
            this.services[key].update()
        }
    }
}
