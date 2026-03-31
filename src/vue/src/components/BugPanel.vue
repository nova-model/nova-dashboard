<template>
    <v-menu activator="parent" :close-on-content-click="false">
        <v-card width="600">
            <v-card-title class="mb-2 px-0">Report Issue</v-card-title>
            <v-card-text class="pa-0">
                <div v-if="!user.is_logged_in">
                    <p>
                        You must be logged in to directly report issues. If you are having
                        difficulty logging in and need to contact us for support, please email us at
                        <a :href="`mailto:${supportEmail}`" target="_blank">{{ supportEmail }}</a
                        >.
                    </p>
                </div>
                <div v-else>
                    <p>
                        If the below form does not work for you, then you may also email us at
                        <a :href="`mailto:${supportEmail}`" target="_blank">{{ supportEmail }}</a
                        >.
                    </p>

                    <div class="issue-form">
                        <v-text-field
                            v-model="email"
                            :maxlength="textFieldMaxLength"
                            label="Email Address"
                            disabled
                        />
                        <v-autocomplete v-model="topic" :items="topics" label="Topic">
                            <template v-slot:item="data">
                                <v-list-item
                                    v-bind="data.props"
                                    class="bg-transparent pl-8"
                                ></v-list-item>
                            </template>
                        </v-autocomplete>
                        <v-textarea
                            v-model="description"
                            :maxlength="descriptionMaxLength"
                            label="Please Describe Your Issue"
                            rows="5"
                            auto-grow
                            counter
                            outlined
                        />
                    </div>

                    <v-btn v-if="!submitting" :disabled="isDisabled" class="mb-4" @click="submit">
                        Submit
                    </v-btn>
                    <v-progress-circular v-else-if="submitting" indeterminate />

                    <p v-if="issueUrl">
                        Issue was opened successfully. We will be in touch soon. You may view your
                        opened issue at
                        <a :href="issueUrl" target="_blank">{{ issueUrl }}</a
                        >.
                    </p>
                    <p v-if="errorMessage">
                        {{ errorMessage }}
                    </p>
                </div>
            </v-card-text>
        </v-card>
    </v-menu>
</template>

<script setup>
import Cookies from "js-cookie"
import { computed, onMounted, ref } from "vue"

import { getTools } from "@/router"
import { useUserStore } from "@/stores/user"

const basePath = import.meta.env.VITE_BASE_PATH
const supportEmail = import.meta.env.VITE_SUPPORT_EMAIL
const categories = getTools()
const user = useUserStore()

const email = ref("")
const topic = ref("")
const description = ref("")
const submitting = ref(false)
const issueUrl = ref("")
const errorMessage = ref("")
const textFieldMaxLength = 100
const descriptionMaxLength = 500
const submissionTimeout = 1000 // one second

const isDisabled = computed(() => !email.value || !topic.value || !description.value)

const keys = []
const topics = ref([
    { type: "subheader", title: "General Issues" },
    "Login Issue",
    "Problem Starting Tools",
    "Other"
])
Object.values(categories).forEach((category) => {
    topics.value.push({ type: "subheader", title: category.name })
    ;[...category.tools, ...category.prototype_tools].forEach((tool) => {
        const key = `${category.name} - ${tool.name}`

        if (!keys.includes(key)) {
            keys.push(key)
            topics.value.push({ title: tool.name, value: key })
        }
    })
})

function reset() {
    setDefaultEmail()
    topic.value = ""
    description.value = ""
    submitting.value = false
}

function setDefaultEmail() {
    if (user.is_logged_in) {
        email.value = user.email
    }
}

async function submit() {
    issueUrl.value = ""
    errorMessage.value = ""
    submitting.value = true

    const response = await fetch(`${basePath}api/issue/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": Cookies.get("csrftoken")
        },
        body: JSON.stringify({
            api_key: user.apiKey,
            email: email.value.slice(0, textFieldMaxLength),
            topic: topic.value,
            description: description.value.slice(0, descriptionMaxLength)
        })
    })

    setTimeout(() => {
        postSubmit(response)
    }, submissionTimeout)
}

async function postSubmit(response) {
    if (response.status === 200) {
        const data = await response.json()

        issueUrl.value = data.url
        errorMessage.value = ""
    } else {
        issueUrl.value = ""
        errorMessage.value = "Something went wrong while submitting your issue. Please try again."
    }

    reset()
}

onMounted(() => {
    setDefaultEmail()
})

defineExpose({ setDefaultEmail })
</script>

<style scoped>
.issue-form > * {
    margin-bottom: 0.5em;
}
</style>
