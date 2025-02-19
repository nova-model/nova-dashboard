import Cookies from "js-cookie"
import { defineStore } from "pinia"

export const useJobStore = defineStore("job", {
    state: () => {
        return {
            autoopen: false,
            callback: null,
            galaxy_error: "",
            jobs: {},
            running: false,
            timeout: 1000,
            monitor_task: null
        }
    },
    actions: {
        async launchJob(tool_id) {
            this.jobs[tool_id] = {
                id: "",
                start: Date.now(),
                submitted: false,
                state: "launching",
                url: ""
            }

            const response = await fetch("/api/galaxy/launch/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": Cookies.get("csrftoken")
                },
                body: JSON.stringify({
                    tool_id: tool_id
                })
            })

            if (response.status === 200) {
                this.running = true
                this.jobs[tool_id].submitted = true
                this.restartMonitor()
            } else {
                this.jobs[tool_id].state = "stopped"

                const data = await response.json()
                this.galaxy_error = `Galaxy error: ${data.error}`
            }
        },
        async stopJob(tool_id) {
            this.jobs[tool_id].state = "stopping"

            const response = await fetch("/api/galaxy/stop/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": Cookies.get("csrftoken")
                },
                body: JSON.stringify({
                    job_id: this.jobs[tool_id].id
                })
            })

            if (response.status === 200) {
                this.running = true
                this.restartMonitor()
            } else {
                this.jobs[tool_id].state = "launched"

                const data = await response.json()
                this.galaxy_error = `Galaxy error: ${data.error}`
            }
        },
        async monitorJobs() {
            const response = await fetch("/api/galaxy/monitor/")
            const data = await response.json()

            if (response.status === 200) {
                let hasErrors = false

                // Look for jobs that are running
                data.jobs.forEach(async (job) => {
                    if (!(job.tool_id in this.jobs)) {
                        this.jobs[job.tool_id] = { start: Date.now(), submitted: false, url: "" }
                    }

                    if (job.state === "error") {
                        hasErrors = true
                        this.galaxy_error = `Galaxy error: ${job.tool_id} is in an error state`

                        if (this.jobs[job.tool_id].state !== "stopping") {
                            this.jobs[job.tool_id].id = job.job_id
                            this.jobs[job.tool_id].state = "error"
                            this.jobs[job.tool_id].submitted = false
                        }
                    }

                    if (job.url) {
                        this.jobs[job.tool_id].url = job.url
                    }

                    if (
                        job.state === "running" &&
                        this.jobs[job.tool_id].state !== "stopping" &&
                        this.jobs[job.tool_id].state !== "launched" &&
                        job.url &&
                        (await this.urlReady(job.url))
                    ) {
                        if (this.autoopen) {
                            window.open(job.url, "_blank")
                        }

                        this.jobs[job.tool_id].id = job.job_id
                        this.jobs[job.tool_id].state = "launched"
                        this.jobs[job.tool_id].submitted = false
                    }
                })

                // Look for jobs that have stopped running
                Object.values(this.jobs).forEach((job) => {
                    // The timestamp key in this.jobs is a Number and needs to be skipped here.
                    if (typeof job !== "object") {
                        return
                    }

                    if (
                        job.state !== "launching" &&
                        !data.jobs.some((target) => target.job_id === job.id)
                    ) {
                        job.state = "stopped"
                    } else if (
                        !data.jobs.some((target) => target.job_id === job.id) &&
                        Date.now() - job.start > 60000
                    ) {
                        // The job hasn't starting reporting its status in one minute, something unexpected has happened.
                        job.state = "error"

                        hasErrors = true
                        this.galaxy_error = `Galaxy error: Tool failed to launch properly for an unknown reason.`
                    }
                })

                if (!hasErrors) {
                    this.galaxy_error = ""
                }
            } else {
                this.galaxy_error = `Galaxy error: ${data.error}`
            }

            // Turn on the spinner in the footer if any job is being started or stopped
            this.running = Object.values(this.jobs).some((job) =>
                ["launching", "stopping"].includes(job.state)
            )

            if (this.callback !== undefined && this.callback !== null) {
                this.callback()
            }

            // Monitor quickly if a job is starting or stopping
            // Delay the monitor if nothing is starting or stopping to avoid spamming the server
            if (this.running) {
                this.timeout = 1000
            } else if (this.timeout < 15000) {
                this.timeout += 1000
            }

            if (this.monitor_task) {
                window.clearTimeout(this.monitor_task)
            }
            this.monitor_task = setTimeout(this.monitorJobs, this.timeout)
        },
        restartMonitor() {
            this.timeout = 1000
            this.monitorJobs()
        },
        startMonitor(user, callback) {
            this.autoopen = user.autoopen
            this.callback = callback
            this.monitorJobs()
        },
        async urlReady(url) {
            try {
                const response = await fetch(url)

                return response.status > 199 && response.status < 300
            } catch {
                return false
            }
        }
    }
})
