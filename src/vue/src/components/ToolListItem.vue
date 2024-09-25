<!-- Creates a VListItem for launching, opening, and stopping a Galaxy tool. -->
<template>
    <v-list-item>
        <v-list-item-title>{{ tool.name }}</v-list-item-title>
        <v-list-item-subtitle>{{ tool.description }}</v-list-item-subtitle>

        <template v-slot:append>
            <v-list-item-action>
                <v-btn v-if="!is_logged_in" disabled>Sign in to run apps</v-btn>
                <div v-else>
                    <v-btn v-if="canLaunch(jobs, tool.id)" @click="job.launchJob(tool.id)">
                        Launch
                        <v-icon>mdi-play</v-icon>
                    </v-btn>
                    <v-btn v-if="canUse(jobs, tool.id)" :href="jobs[tool.id]?.url" target="_blank">
                        Open
                        <v-icon>mdi-open-in-new</v-icon>
                    </v-btn>
                    <v-btn
                        v-if="canStop(jobs, tool.id)"
                        color="error"
                        @click="job.stopJob(tool.id)"
                    >
                        Stop
                        <v-icon>mdi-stop</v-icon>
                    </v-btn>
                    <v-progress-circular v-if="isChanging(jobs, tool.id)" indeterminate />
                </div>
            </v-list-item-action>
        </template>
    </v-list-item>
</template>

<script setup>
import { storeToRefs } from "pinia"

import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"

const props = defineProps({
    index: {
        required: true,
        type: Number
    },
    tool: {
        required: true,
        type: Object
    }
})

const job = useJobStore()
const { jobs } = storeToRefs(job)
const user = useUserStore()
const { is_logged_in } = storeToRefs(user)

function canLaunch(jobs, tool_id) {
    return !["error", "launching", "launched", "stopping"].includes(jobs[tool_id]?.state)
}

function canUse(jobs, tool_id) {
    return jobs[tool_id]?.state === "launched"
}

function canStop(jobs, tool_id) {
    return ["launched", "error"].includes(jobs[tool_id]?.state)
}

function isChanging(jobs, tool_id) {
    return ["launching", "stopping"].includes(jobs[tool_id]?.state)
}
</script>
