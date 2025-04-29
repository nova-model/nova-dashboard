<!-- Creates a popover VMenu for viewing all currently active tools in Galaxy. -->
<template>
    <v-btn v-show="toolList.length > 0" icon>
        <v-badge :content="toolList.length">
            <v-icon>mdi-laptop</v-icon>
        </v-badge>

        <v-menu v-if="toolList.length > 0" activator="parent" :close-on-content-click="false">
            <v-card>
                <v-card-title>Active Tools</v-card-title>

                <v-list>
                    <ToolListItem v-for="(tool, index) in toolList" :key="index" :tool="tool" />
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
const { jobs } = storeToRefs(job)

const jobList = computed(() => {
    return Object.entries(jobs.value)
})

const toolList = computed(() => {
    const tools = getTools()

    // Returns all tools connected with a Galaxy job
    const runningTools = []
    Object.values(tools).forEach((tool_category) => {
        let all_tools = tool_category.tools
        if (tool_category.prototype_tools !== undefined) {
            all_tools = all_tools.concat(tool_category.prototype_tools)
        }
        all_tools.forEach((tool) => {
            jobList.value.forEach(([job_tool_id, job]) => {
                if (
                    tool.id === job_tool_id &&
                    job.state === "launched" &&
                    !runningTools.some((target) => target.id === tool.id)
                ) {
                    runningTools.push(tool)
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
