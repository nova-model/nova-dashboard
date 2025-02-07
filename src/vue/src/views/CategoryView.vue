<!-- Defines the content when the user is viewing a category's tool list. -->
<template>
    <v-breadcrumbs class="position-fixed">
        <v-breadcrumbs-item to="/">Home</v-breadcrumbs-item>
        <v-breadcrumbs-divider />
        <v-breadcrumbs-item>{{ props.tools[route.params.category].name }}</v-breadcrumbs-item>
    </v-breadcrumbs>

    <v-container class="align-start d-flex justify-center mt-16">
        <v-card width="800">
            <v-card-title class="text-center">
                {{ tools[route.params.category].name }} Applications
            </v-card-title>
            <v-card-subtitle>
                The below tools are currently supported for running on Calvera. You must be signed
                in to launch them. You may sign in using the button in the top right corner of this
                page.
            </v-card-subtitle>

            <v-card-text>
                <v-banner v-if="galaxy_error" class="bg-error text-center">{{
                    galaxy_error
                }}</v-banner>

                <v-list>
                    <v-list-subheader v-if="tools[route.params.category].tools.length > 0">
                        Available Tools
                    </v-list-subheader>
                    <v-list-subheader v-else class="justify-center">
                        Stay tuned, we will be adding tools here soon!
                    </v-list-subheader>

                    <ToolListItem
                        v-for="(tool, index) in tools[route.params.category].tools"
                        :key="index"
                        :tool="tool"
                        class="pa-2"
                    />
                </v-list>
            </v-card-text>
        </v-card>
    </v-container>
</template>

<script setup>
import { onMounted } from "vue"
import { storeToRefs } from "pinia"
import { useRoute } from "vue-router"

import ToolListItem from "@/components/ToolListItem.vue"
import { useJobStore } from "@/stores/job"
import { useUserStore } from "@/stores/user"

const props = defineProps({
    tools: {
        required: true,
        type: Object
    }
})
const route = useRoute()

const job = useJobStore()
const { galaxy_error } = storeToRefs(job)
const user = useUserStore()

onMounted(async () => {
    if (user.is_logged_in) {
        job.startMonitor(user)
    } else {
        window.localStorage.setItem("lastpath", route.path)
        window.localStorage.setItem("redirect", true)
    }
})
</script>

<style scoped>
.v-breadcrumbs {
    top: 64px;
}
</style>
