<template>
    <v-list>
        <v-list-subheader>General Tools</v-list-subheader>

        <ToolListItem v-for="(tool, index) in props.tools" :key="index" :tool="tool" class="pa-2" />
    </v-list>
</template>

<script setup>
import ToolListItem from "@/components/ToolListItem.vue"

const props = defineProps({
    tools: {
        required: true,
        type: Array
    }
})
</script>
