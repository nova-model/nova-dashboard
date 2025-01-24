<!-- Creates a popover VMenu for viewing all currently active tools in Galaxy. -->
<template>
    <v-btn v-show="tool_list.length > 0" icon>
        <v-badge :content="tool_list.length">
            <v-icon>mdi-laptop</v-icon>
        </v-badge>

        <v-menu v-if="tool_list.length > 0" activator="parent" :close-on-content-click="false">
            <v-card>
                <v-card-title>Active Tools</v-card-title>

                <v-list>
                    <ToolListItem v-for="(tool, index) in tool_list" :key="index" :tool="tool" />
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

const job_list = computed(() => {
    return Object.entries(jobs.value)
})

const tool_list = computed(() => {
    const tools = getTools()

    // Returns all tools connected with a Galaxy job
    const running_tools = []
    Object.values(tools).forEach((tool_category) => {
        tool_category.tools.forEach((tool) => {
            job_list.value.forEach(([job_tool_id, job]) => {
                if (tool.id === job_tool_id && job.state === "launched") {
                    running_tools.push(tool)
                }
            })
        })
    })

    return running_tools
})
</script>

<style scoped>
.v-badge:deep(.v-badge__badge) {
    letter-spacing: 0;
}
</style>
