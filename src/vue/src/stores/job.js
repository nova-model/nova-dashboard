import Cookies from "js-cookie"
import { defineStore } from "pinia"
import { nextTick } from "vue"

const galaxy_url = import.meta.env.VITE_GALAXY_URL

export const useJobStore = defineStore("job", {
    state: () => {
        return {
            user: null,
            allow_autoopen: true,
            callback: null,
            galaxy_error: "",
            has_monitored: false,
            jobs: {},
            running: false,
            timeout: 1000,
            timeout_error: false,
            timeout_duration: 60000,
            error_reset_duration: 15000,
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
                url: "",
                url_ready: false
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
                const data = await response.json()
                this.jobs[tool_id].id = data.id
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

                    if (job.state === "error") {
                        hasErrors = true
                        this.galaxy_error = `Galaxy error: ${job.tool_id} is in an error state`

                        if (this.jobs[job.tool_id].state !== "stopping") {
                            this.jobs[job.tool_id].id = job.job_id
                            this.jobs[job.tool_id].state = "error"
                            this.jobs[job.tool_id].submitted = false

                            // Clear the launch error
                            setTimeout(() => {
                                delete this.jobs[job.tool_id]
                            }, this.error_reset_duration)
                        }
                    }

                    if (job.url && !this.jobs[job.tool_id].url_ready) {
                        this.jobs[job.tool_id].url = job.url
                        this.jobs[job.tool_id].url_ready = job.url_ready
                    }

                    if (
                        job.state === "running" &&
                        this.jobs[job.tool_id].state !== "stopping" &&
                        this.jobs[job.tool_id].state !== "launched" &&
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

                        this.jobs[job.tool_id].id = job.job_id
                        this.jobs[job.tool_id].state = "launched"
                        this.jobs[job.tool_id].submitted = false
                    }
                }

                // Look for jobs that have stopped running
                Object.keys(this.jobs).forEach((tool_id) => {
                    const job = this.jobs[tool_id]

                    if (
                        job.state !== "launching" &&
                        !data.jobs.some((target) => target.job_id === job.id)
                    ) {
                        // Tool stopped gracefully
                        delete this.jobs[tool_id]
                    } else if (
                        !data.jobs.some((target) => target.job_id === job.id) &&
                        Date.now() - job.start > this.timeout_duration
                    ) {
                        // The job hasn't starting reporting its status in one minute, something unexpected has happened.
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

            // nextTick ensures that any updates to the UI from this monitoring loop have been committed.
            // Setting this flag will allow users to launch tools, which should only be possible after
            // the UI has been updated with the results of the initial monitoring.
            nextTick(() => {
                this.has_monitored = true
            })
        },
        restartMonitor() {
            this.timeout = 1000
            this.monitorJobs()
        },
        startMonitor(user, allow_autoopen, callback) {
            this.user = user
            this.allow_autoopen = allow_autoopen
            this.callback = callback
            this.monitorJobs()
        }
    }
})
