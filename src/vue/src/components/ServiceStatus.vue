<template>
    <div>
        <v-list-group v-if="service.countText">
            <template v-slot:activator="{ props }">
                <v-list-item v-bind="props" class="bg-white border-none">
                    <template v-slot:prepend>
                        <v-icon :color="AlertManager.statusColor(service.status)">
                            {{ AlertManager.statusIcon(service.status) }}
                        </v-icon>
                    </template>

                    <v-list-item-title>
                        {{ service.name }}{{ service.countText }}
                    </v-list-item-title>
                </v-list-item>
            </template>

            <ServiceStatus v-for="child in service.children" :service="child" />
        </v-list-group>
        <v-list-item v-else class="bg-white border-none">
            <template v-slot:prepend>
                <v-icon :color="AlertManager.statusColor(service.status)">
                    {{ AlertManager.statusIcon(service.status) }}
                </v-icon>
            </template>

            <v-list-item-title>
                {{ service.name }}
            </v-list-item-title>
        </v-list-item>
    </div>
</template>

<script setup>
import AlertManager from "@/assets/js/alerts"

const props = defineProps({
    service: {
        required: true,
        type: Object
    }
})

const service = props.service
</script>
