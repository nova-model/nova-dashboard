import Cookies from "js-cookie"
import { defineStore } from "pinia"

export const useJobStore = defineStore("job", {
    state: () => {
        return {
            galaxy_error: "",
            jobs: {},
            running: false
        }
    },
    actions: {
        async launchJob(tool_id) {
            this.jobs[tool_id] = { id: "", start: Date.now(), state: "launching", url: "" }

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
            } else {
                this.jobs[tool_id].state = "stopped"

                const data = await response.json()
                this.galaxy_error = `Galaxy error: ${data.error}`
            }

            // This ensures we don't lose track of the job if the user refreshes immediately after launch
            this.saveToLocalStorage()
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
            } else {
                this.jobs[tool_id].state = "launched"

                const data = await response.json()
                this.galaxy_error = `Galaxy error: ${data.error}`
            }
        },
        async monitorJobs(autoopen, force) {
            if (!force && !this.running) {
                return
            }

            const response = await fetch("/api/galaxy/monitor/")
            const data = await response.json()

            if (response.status === 200) {
                let hasErrors = false

                // Look for jobs that are running
                data.jobs.forEach(async (job) => {
                    if (!(job.tool_id in this.jobs)) {
                        this.jobs[job.tool_id] = { start: Date.now() }
                    }

                    if (job.state === "error") {
                        hasErrors = true
                        this.galaxy_error = `Galaxy error: ${job.tool_id} is in an error state`

                        if (this.jobs[job.tool_id].state !== "stopping") {
                            this.jobs[job.tool_id].id = job.job_id
                            this.jobs[job.tool_id].state = "error"
                        }
                    }

                    if (
                        job.state === "running" &&
                        this.jobs[job.tool_id].state !== "stopping" &&
                        this.jobs[job.tool_id].state !== "launched" &&
                        job.url &&
                        (await this.urlReady(job.url))
                    ) {
                        if (autoopen) {
                            window.open(job.url, "_blank")
                        }

                        this.jobs[job.tool_id].id = job.job_id
                        this.jobs[job.tool_id].state = "launched"
                        this.jobs[job.tool_id].url = job.url
                    }
                })

                // Look for jobs that have stopped running
                Object.values(this.jobs).forEach((job) => {
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

            this.saveToLocalStorage()

            // Turn on the spinner in the footer if any job is being started or stopped
            this.running = Object.values(this.jobs).some((job) =>
                ["launching", "stopping"].includes(job.state)
            )
        },
        startMonitor(user) {
            this.loadFromLocalStorage()
            this.monitorJobs(false, true)
            setInterval(() => {
                this.monitorJobs(user.autoopen, false)
            }, 2000)
        },
        loadFromLocalStorage() {
            const data = window.localStorage.getItem("job_state")
            let job_states = {}
            if (data !== null) {
                job_states = JSON.parse(data)
            }

            for (let key in job_states) {
                if (job_states[key].state !== "stopped") {
                    this.jobs[key] = job_states[key]
                }
            }
        },
        saveToLocalStorage() {
            window.localStorage.setItem("job_state", JSON.stringify(this.jobs))
        },
        async urlReady(url) {
            const response = await fetch(url)

            return response.status > 199 && response.status < 300
        }
    }
})
