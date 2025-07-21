import Cookies from "js-cookie"
import { defineStore } from "pinia"
import { nextTick } from "vue"

import { useUserStore } from "@/stores/user"

const galaxy_url = import.meta.env.VITE_GALAXY_URL

export const useJobStore = defineStore("job", {
    state: () => {
        return {
            user: useUserStore(),
            allow_autoopen: true,
            callback: null,
            galaxy_error: "",
            has_monitored: false,
            jobs: {},
            running: false,
            timeout: 2000,
            timeout_error: false,
            timeout_duration: 60000,
            error_reset_duration: 15000,
            monitor_interval: null
        }
    },
    actions: {
        async launchJob(tool_id, inputs) {
            this.jobs[tool_id] = {
                id: "",
                start: Date.now(),
                submitted: true,
                state: "submitting",
                url: "",
                url_ready: false
            }
            this.updateCalveraSpinner()

            await this.user.userStatus()
            if (this.requires_galaxy_login) {
                this.jobs[tool_id].state = "stopped"
                return
            }

            const response = await fetch("/api/galaxy/launch/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": Cookies.get("csrftoken")
                },
                body: JSON.stringify({
                    tool_id: tool_id,
                    inputs: inputs
                })
            })

            if (response.status === 200) {
                this.running = true
                const data = await response.json()
                this.jobs[tool_id].id = data.id
            } else {
                this.jobs[tool_id].state = "stopped"

                const data = await response.json()
                this.galaxy_error = `Galaxy error: ${data.error}`
            }
        },
        async stopJob(tool_id) {
            this.jobs[tool_id].state = "stopping"
            this.updateCalveraSpinner()

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
            } else {
                this.jobs[tool_id].state = "ready"

                const data = await response.json()
                this.galaxy_error = `Galaxy error: ${data.error}`
            }
        },
        async monitorJobs() {
            const job_ids = {}
            for (const j in this.jobs) {
                job_ids[j] = this.jobs[j].id
            }
            const response = await fetch("/api/galaxy/monitor/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": Cookies.get("csrftoken")
                },
                body: JSON.stringify({ tool_ids: job_ids })
            })
            const data = await response.json()

            if (response.status === 200) {
                let hasErrors = false

                // Look for jobs that are running
                for (const job of data.jobs) {
                    if (!(job.tool_id in this.jobs)) {
                        this.jobs[job.tool_id] = {
                            id: job.job_id,
                            start: Date.now(),
                            submitted: false,
                            url: "",
                            url_ready: false
                        }
                    }

                    this.jobs[job.tool_id].id = job.job_id
                    if (!["ready", "stopping"].includes(this.jobs[job.tool_id].state)) {
                        this.jobs[job.tool_id].state = job.state
                    }

                    if (["deleted", "deleting", "ok"].includes(job.state)) {
                        delete this.jobs[job.tool_id]
                    } else if (job.state === "error") {
                        hasErrors = true
                        this.galaxy_error = `Galaxy error: ${job.tool_id} is in an error state`

                        // Clear the launch error
                        setTimeout(() => {
                            delete this.jobs[job.tool_id]
                        }, this.error_reset_duration)
                    }

                    if (job.url && !this.jobs[job.tool_id].url_ready) {
                        this.jobs[job.tool_id].url = job.url
                        this.jobs[job.tool_id].url_ready = job.url_ready
                    }

                    if (
                        job.state === "running" &&
                        this.jobs[job.tool_id].state !== "stopping" &&
                        this.jobs[job.tool_id].state !== "ready" &&
                        job.url_ready
                    ) {
                        this.user.getAutoopen()
                        if (
                            this.user.autoopen &&
                            this.allow_autoopen &&
                            this.jobs[job.tool_id].submitted
                        ) {
                            window.open(job.url, "_blank")
                        }

                        this.jobs[job.tool_id].state = "ready"
                    }
                }

                // Look for jobs that have stopped running
                Object.keys(this.jobs).forEach((tool_id) => {
                    const job = this.jobs[tool_id]

                    if (
                        !["submitting", "new", "queued", "running"].includes(job.state) &&
                        !data.jobs.some((target) => target.job_id === job.id)
                    ) {
                        // Tool stopped gracefully
                        delete this.jobs[tool_id]
                    } else if (
                        !["error", "running", "ready"].includes(job.state) &&
                        Date.now() - job.start > this.timeout_duration
                    ) {
                        // The job hasn't started in one minute, something unexpected has happened.
                        job.state = "error"

                        this.timeout_error = true
                        setTimeout(() => {
                            delete this.jobs[tool_id]
                            this.timeout_error = false
                        }, this.error_reset_duration)
                        this.galaxy_error = `Galaxy error: Tool failed to respond within one minute. This may be due to an outage on ${galaxy_url}.`
                    }
                })

                if (!hasErrors && !this.timeout_error) {
                    this.galaxy_error = ""
                }
            } else {
                this.galaxy_error = `Galaxy error: ${data.error}`
            }

            this.updateCalveraSpinner()

            if (this.callback !== undefined && this.callback !== null) {
                this.callback()
            }

            // nextTick ensures that any updates to the UI from this monitoring loop have been committed.
            // Setting this flag will allow users to launch tools, which should only be possible after
            // the UI has been updated with the results of the initial monitoring.
            nextTick(() => {
                this.has_monitored = true
            })
        },
        startMonitor(allow_autoopen, callback) {
            this.allow_autoopen = allow_autoopen
            this.callback = callback

            if (this.monitor_interval === null) {
                this.monitorJobs()
            } else {
                window.clearInterval(this.monitor_interval)
                this.monitor_interval = null
            }

            this.monitor_interval = window.setInterval(this.monitorJobs, this.timeout)
        },
        updateCalveraSpinner() {
            // Turn on the spinner in the footer if any job is being started or stopped
            this.running = Object.values(this.jobs).some((job) => {
                return ["submitting", "new", "queued", "running", "stopping"].includes(job.state)
            })
        }
    }
})
