<template>
    <v-list v-if="props.toolData.tools?.length > 0">
        <v-list-subheader>General Tools</v-list-subheader>
        <ToolListItem
            v-for="(tool, index) in props.toolData.tools"
            :key="index"
            :tool="tool"
            class="pa-2"
        />
    </v-list>

    <v-list v-if="props.toolData.prototype_tools?.length > 0">
        <v-list-subheader> Prototype Tools </v-list-subheader>

        <ToolListItem
            v-for="(tool, index) in props.toolData.prototype_tools"
            :key="index"
            :tool="tool"
            class="pa-2"
        />
    </v-list>
</template>

<script setup>
import ToolListItem from "@/components/ToolListItem.vue"

const props = defineProps({
    toolData: {
        required: true,
        type: Object
    }
})
</script>
