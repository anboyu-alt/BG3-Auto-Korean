---@diagnostic disable: undefined-field
local ConfigUtils = Ext.Require("Shared/ConfigUtils.lua")

local rootTemplatesCache = {}
local localTemplatesCache = {}
local activeConfig = {}
local CHUNK_SIZE = 500
local APPLY_RETRY_DELAYS = { 250, 1000, 2500 }
local applyGeneration = 0

local function GetModName(modUUID)
    if not modUUID or modUUID == "" then return "Vanilla" end
    local modInfo = Ext.Mod.GetMod(modUUID)
    if modInfo and modInfo.Info and modInfo.Info.Name then
        local name = modInfo.Info.Name
        local excludedMods = { Shared = true, Gustav = true, SharedDev = true, GustavDev = true }
        if excludedMods[name] then return "Vanilla" end
        return name
    end
    return "Unknown Mod"
end

local function GetTemplateName(template, useDisplayName)
    if useDisplayName and template.DisplayName and template.DisplayName.Handle and template.DisplayName.Handle.Handle then
        local translatedName = Ext.Loca.GetTranslatedString(template.DisplayName.Handle.Handle)
        if translatedName and translatedName ~= "" then return translatedName end
    end
    if template.Name and template.Name ~= "" then return template.Name end
    local success, mapKey = pcall(function() return template.MapKey end)
    if success and mapKey and mapKey ~= "" then return mapKey end
    return "Unknown"
end

local function ProcessTemplate(uuid, template, scope, statTypeMap)
    if not template or template.TemplateType ~= "item" then return nil end
    local rootTemplateId = nil
    if scope == "Local" then
        rootTemplateId = template.TemplateName
    end
    local itemType = "Unknown"
    local templateMod = "Vanilla"
    local success_modid, result_modid = pcall(function() return template.ModId end)
    if success_modid and result_modid then templateMod = GetModName(result_modid) end
    local statMod = "Vanilla"
    if template.Stats and template.Stats ~= "" then
        itemType = statTypeMap[template.Stats] or "Object"
        local stat = Ext.Stats.Get(template.Stats)
        if stat and stat.ModId and stat.ModId ~= "" then
            statMod = GetModName(stat.ModId)
        end
    end
    local sourceMod = (statMod ~= "Vanilla") and statMod or templateMod
    local isContainer = false
    if template.InventoryType and template.OnUsePeaceActions then
        for _, action in ipairs(template.OnUsePeaceActions) do
            if action and action.Type == "OpenClose" then
                isContainer = true
                break
            end
        end
    end
    return {
        uuid = uuid,
        rootTemplateId = rootTemplateId,
        displayName = GetTemplateName(template, true),
        internalName = GetTemplateName(template, false),
        icon = template.Icon,
        defaultTooltip = template.Tooltip or 1,
        canBePickedUp = template.CanBePickedUp or false,
        itemType = itemType,
        sourceMod = sourceMod,
        isContainer = isContainer,
    }
end


local function BuildRootTemplateCache()
    rootTemplatesCache = {}
    local statTypeMap = {}
    local statTypesToScan = { "Armor", "Weapon", "Character", "Object", "PassiveData", "SpellData", "StatusData",
        "InterruptData", "TreasureTable", "TreasureCategory" }
    for _, statType in ipairs(statTypesToScan) do
        local statNames = Ext.Stats.GetStats(statType)
        if statNames then
            for _, statName in ipairs(statNames) do statTypeMap[statName] = statType end
        end
    end
    local allTemplates = Ext.Template.GetAllRootTemplates()
    if not allTemplates then return end
    for uuid, template in pairs(allTemplates) do
        local success, result = pcall(ProcessTemplate, uuid, template, "Root", statTypeMap)
        if success and result then
            table.insert(rootTemplatesCache, result)
        end
    end
end

local function BuildLocalTemplateCache()
    localTemplatesCache = {}
    local statTypeMap = {}
    local statTypesToScan = { "Armor", "Weapon", "Character", "Object", "PassiveData", "SpellData", "StatusData",
        "InterruptData", "TreasureTable", "TreasureCategory" }
    for _, statType in ipairs(statTypesToScan) do
        local statNames = Ext.Stats.GetStats(statType)
        if statNames then
            for _, statName in ipairs(statNames) do statTypeMap[statName] = statType end
        end
    end
    local localTemplates = Ext.Template.GetAllLocalTemplates()
    if not localTemplates then return end
    for uuid, template in pairs(localTemplates) do
        local success, result = pcall(ProcessTemplate, uuid, template, "Local", statTypeMap)
        if success and result then
            table.insert(localTemplatesCache, result)
        end
    end
end

local function GetRootTemplateId(template)
    local success, templateName = pcall(function() return template.TemplateName end)
    if success and templateName and templateName ~= "" then
        return templateName
    end
    return nil
end

local function ResolveConfigValue(uuid, template, scope)
    local rootTemplateId = nil
    if scope == "Local" then
        rootTemplateId = GetRootTemplateId(template)
    end
    return ConfigUtils.GetEffectiveValue(activeConfig, uuid, rootTemplateId)
end

local function ApplyConfigToRootTemplates()
    local allTemplates = Ext.Template.GetAllRootTemplates()
    if not allTemplates then return end
    ---@param template ItemTemplate
    for uuid, template in pairs(allTemplates) do
        if template.TemplateType == "item" and template.Tooltip ~= nil then
            local value = ResolveConfigValue(uuid, template, "Root")
            if value ~= nil then template.Tooltip = value end
        end
    end
end

local function ApplyConfigToLocalTemplates()
    local localTemplates = Ext.Template.GetAllLocalTemplates()
    if not localTemplates then return end
    ---@param template ItemTemplate
    for uuid, template in pairs(localTemplates) do
        if template.TemplateType == "item" and template.Tooltip ~= nil then
            local value = ResolveConfigValue(uuid, template, "Local")
            if value ~= nil then template.Tooltip = value end
        end
    end
end

local function ApplyActiveConfig()
    ApplyConfigToRootTemplates()
    ApplyConfigToLocalTemplates()
end

local function ScheduleConfigReapply()
    applyGeneration = applyGeneration + 1
    local generation = applyGeneration
    local function applyIfCurrent()
        if generation ~= applyGeneration then return end
        ApplyActiveConfig()
    end

    applyIfCurrent()
    for _, delay in ipairs(APPLY_RETRY_DELAYS) do
        Ext.Timer.WaitFor(delay, applyIfCurrent)
    end
end

local function SendTemplatesInChunks(userId)
    local totalRoot = #rootTemplatesCache
    local totalLocal = #localTemplatesCache
    local totalChunks = math.ceil(totalRoot / CHUNK_SIZE) + math.ceil(totalLocal / CHUNK_SIZE)
    local currentChunk = 0 -- gotta chunk it cuz the size is too big -.-
    for i = 1, totalRoot, CHUNK_SIZE do
        currentChunk = currentChunk + 1
        local chunk = {}
        for j = i, math.min(i + CHUNK_SIZE - 1, totalRoot) do
            table.insert(chunk, rootTemplatesCache[j])
        end
        local message = {
            chunkIndex = currentChunk,
            totalChunks = totalChunks,
            scope = "Root",
            templates = chunk
        }
        Ext.ServerNet.PostMessageToUser(userId, "TooltipManager_ReceiveChunk", Ext.Json.Stringify(message))
    end
    for i = 1, totalLocal, CHUNK_SIZE do
        currentChunk = currentChunk + 1
        local chunk = {}
        for j = i, math.min(i + CHUNK_SIZE - 1, totalLocal) do
            table.insert(chunk, localTemplatesCache[j])
        end
        local message = {
            chunkIndex = currentChunk,
            totalChunks = totalChunks,
            scope = "Local",
            templates = chunk
        }
        Ext.ServerNet.PostMessageToUser(userId, "TooltipManager_ReceiveChunk", Ext.Json.Stringify(message))
    end
end

Ext.RegisterNetListener("TooltipManager_RequestTemplates", function(channel, payload, userId)
    BuildRootTemplateCache()
    BuildLocalTemplateCache()
    SendTemplatesInChunks(userId)
end)

local pendingConfig = {}
local receivedConfigChunks = 0
local expectedConfigChunks = 0

Ext.RegisterNetListener("TooltipManager_ApplyConfigChunk", function(channel, payload, userId)
    local success, data = pcall(Ext.Json.Parse, payload)
    if not success or type(data) ~= "table" then return end

    if data.chunkIndex == 1 then
        pendingConfig = {}
        receivedConfigChunks = 0
        expectedConfigChunks = data.totalChunks
    end

    for key, value in pairs(data.config) do
        pendingConfig[key] = value
    end

    receivedConfigChunks = receivedConfigChunks + 1

    if receivedConfigChunks >= expectedConfigChunks then
        activeConfig = pendingConfig
        ScheduleConfigReapply()
        pendingConfig = {}
    end
end)

Ext.RegisterNetListener("TooltipManager_ApplyConfig", function(channel, payload, userId)
    local success, config = pcall(Ext.Json.Parse, payload)
    if success and type(config) == "table" then
        activeConfig = config
        ScheduleConfigReapply()
    end
end)

Ext.Osiris.RegisterListener("LevelGameplayStarted", 2, "after", function(levelName, isEditorMode)
    BuildRootTemplateCache()
    BuildLocalTemplateCache()
    ScheduleConfigReapply()
end)

Ext.Events.ResetCompleted:Subscribe(function()
    BuildRootTemplateCache()
    BuildLocalTemplateCache()
    ScheduleConfigReapply()
end)
