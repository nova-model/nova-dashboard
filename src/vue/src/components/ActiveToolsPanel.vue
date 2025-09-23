<!-- Creates a popover VMenu for viewing all currently active tools in Galaxy. -->
<template>
    <v-btn v-show="toolList.length > 0" icon>
        <v-badge :content="toolList.length">
            <v-icon>mdi-laptop</v-icon>
        </v-badge>

        <v-menu
            v-if="toolList.length > 0"
            :close-on-content-click="false"
            activator="parent"
            max-width="1200"
        >
            <v-card>
                <v-card-title>Active Tools</v-card-title>

                <v-list>
                    <ToolListItem
                        v-for="(data, index) in toolList"
                        :key="index"
                        :tool="data.tool"
                        :job="data.job"
                    />
                </v-list>
            </v-card>
        </v-menu>
    </v-btn>
</template>

<script setup>
import { storeToRefs } from "pinia"
import { computed } from "vue"

import ToolListItem from "@/components/ToolListItem.vue"
import { getTools } from "@/router"
import { useJobStore } from "@/stores/job"

const job = useJobStore()
const { all_jobs, jobs } = storeToRefs(job)

const jobList = computed(() => {
    return Object.entries(jobs.value)
})

const toolList = computed(() => {
    const tools = getTools()

    // Returns all tools connected with a Galaxy job
    const runningTools = []
    Object.values(tools).forEach((toolCategory) => {
        let all_tools = toolCategory.tools
        if (toolCategory.prototype_tools !== undefined) {
            all_tools = all_tools.concat(toolCategory.prototype_tools)
        }
        all_tools.forEach((tool) => {
            jobList.value.forEach(([job_tool_id, job]) => {
                if (
                    tool.id === job_tool_id &&
                    job.state === "ready" &&
                    !runningTools.some((target) => target.id === tool.id)
                ) {
                    runningTools.push({ job: null, tool: tool })
                }
            })

            all_jobs.value.forEach((job) => {
                if (job.is_datafile_tool && tool.id === job.tool_id && job.url_ready) {
                    runningTools.push({ job: job, tool: tool })
                }
            })
        })
    })

    return runningTools
})
</script>

<style scoped>
.v-badge:deep(.v-badge__badge) {
    letter-spacing: 0;
}
</style>
