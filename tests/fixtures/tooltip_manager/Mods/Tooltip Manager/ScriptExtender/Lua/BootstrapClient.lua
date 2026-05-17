---@diagnostic disable: undefined-field, inject-field

local ConfigUtils = Ext.Require("Shared/ConfigUtils.lua")

local iconBlacklist = {
    ["Portrait_BLD_Humans_Dungeon_Altar_A"] = true,
    ["GEN_Metal_Hinges"] = true,
    ["Item_Cont_Barrel_A"] = true,
    ["Item_CONT_Chest_Ornate_Fortress_A"] = true,
    ["Item_Helper_A"] = true,
    ["DEC_GTY_Eggs_Fetus_A_Shell_A"] = true,
    ["Portrait_Gen_Lever_A"] = true,
    ["MAG_Illithid_Carapace_Boots"] = true,
    ["Item_EQ_Armor_StarterLeather_A_Upperbody_A"] = true,
    ["Item_PUZ_Trap_Mine_A_Red"] = true,
    ["Item_GRN_OilFlask_Blessed"] = true,
    ["Item_FUR_Humans_Canvas_A_Empty"] = true,
    ["Item_GRN_Love"] = true,
    ["Item_LOOT_Scraps_Wood_A"] = true,
    ["Portrait_FUR_Humans_Pris_Cage_Door_A"] = true,
    ["Item_CONT_Chest_Steel_Fortress_A"] = true,
    ["Portrait_Gen_Button_A"] = true,
    ["Item_DLC_Wand_Blue"] = true,
    ["Portrait_Gen_Hatch_Wood_A"] = true,
    ["Item_CONT_Wood_A"] = true,
    ['AMX_Item_AMX_BELT_PAREO_LIGHTBLUE_1C'] = true,
    ['AMX_Item_AMX_DISNEY_JASMINE_RED_1A'] = true,
    ['AMX_Item_AMX_PAREO_1'] = true,
    ['AMX_Item_AMX_PAREO_2'] = true,
    ['AMX_Item_AMX_PAREO_3'] = true,
    ['AMX_Item_AMX_SERAPH_ARMLETS_1A'] = true,
    ['AMX_Item_AMX_TEST_MONK_1A'] = true,
    ['AMX_Item_AMX_UNDERWEAR_ELFBARBARIAN_LIGHTBLUE_FULL_1A'] = true,
    ['JWL_Item_DI_BookManySpells'] = true,
    ['AMX_Item_AMX_BELT_B_1A_BLACK'] = true,
    ['CBR_Item_Shar_Pants'] = true,
    ['Portrait_LTS_Campfire_A'] = true,
    ['slutty_bhaal_babe_icon'] = true,
    ['FRA_Item_FRA_Asmodean_ArbiterDiadem_B'] = true,
    ['FRA_Item_FRA_Flameshade_Chitin_B'] = true,
    ['AMX_Item_AMX_OBJ_Backpack_MaleOutfits'] = true,
    ['AMX_Item_AMX_OBJ_Backpack_MaleOutfits_2'] = true,
    ['AMX_Item_AMX_OBJ_Backpack_MaleOutfits_3'] = true,
    ['Item_LOOT_SCROLL_SappingSting'] = true,
    ['Item_LOOT_SCROLL_MagnifyGravity'] = true,
    ['ARM_Troubadour'] = true,
    ['ARM_Troubadour_Alfira'] = true,
    ['ARM_Troubadour_Shoes'] = true,
    ['Item_Snare_Trap'] = true,
    ['ARM_Troubadour_Volo'] = true,
    ['ARM_Troubadour_Shoes_Brown'] = true,
    ['ICO_CRUEL_REFLECTION'] = true,
    ['ICO_CURSE_OF_HAEMORRHAGING'] = true,
    ['Action_EnchantingRest'] = true,
    ['Action_SacredBenediction'] = true,
    ['ICON_GLOAM_FIELD'] = true,
    ['Action_ImpossibleSong'] = true,
    ['Action_RousingPerformance'] = true,
    ['Action_SoulOfBattle'] = true,
    ['statIcon_WildMagicBarbarianD100_MagicMissileTarget'] = true,
    ['statIcon_WildMagicBarbarianD100_RegainAllSorceryPoints'] = true,
    ['Action_WingsOfTheStorm'] = true,
    ['WSO_Spell_GiantBadger_Burrow'] = true,
    ['WSO_WildShape_Snake'] = true,
}
local itemTemplatesCache = {}
local masterConfig = {}
local activeConfig = {}
local TooltipManagerTab = nil
local itemsTable = nil
local searchInput = nil
local presetCombo = nil
local deletePresetBtn = nil
local searchDebounceTimer = nil
local modFolderPath = "Tooltip Manager"
local importExportStatusText = nil
local filterGroup = nil
local itemCountText = nil
local mainContentHolder = nil
local isTableLoaded = false
local filteredItemList = {}

local allItemTypes = { "All" }
local allSourceMods = { "All" }
local filterOptions = {
    editedStatus = "All",
    modStatus = "All",
    lootableStatus = "All",
    containerStatus = "All",
    itemType = "All",
    sourceMod = "All",
    visibilityState = "All",
    templateScope = "Root",
}

local function MigrateConfig()
    if not masterConfig.presets then return end
    for _, preset in pairs(masterConfig.presets) do
        for uuid, value in pairs(preset) do
            if type(value) == "number" then
                preset[uuid] = { value, value }
            end
        end
    end
end

local function ReadConfig()
    local file = Ext.IO.LoadFile(modFolderPath .. "/config.json")
    local loadedConfig = {}
    if file and file ~= "" then
        local success, result = pcall(Ext.Json.Parse, file)
        if success and type(result) == "table" then loadedConfig = result end
    end
    loadedConfig.presets = loadedConfig.presets or {}
    if not loadedConfig.presets["Default"] then loadedConfig.presets["Default"] = {} end
    loadedConfig.activePresetName = loadedConfig.activePresetName or "Default"
    if not loadedConfig.presets[loadedConfig.activePresetName] then loadedConfig.activePresetName = "Default" end
    masterConfig = loadedConfig
    MigrateConfig()
    activeConfig = masterConfig.presets[masterConfig.activePresetName]
end

local function GetConfigValue(uuid)
    return ConfigUtils.GetEntryValue(activeConfig[uuid])
end

local function GetOriginalValue(uuid)
    return ConfigUtils.GetEntryOriginalValue(activeConfig[uuid])
end

local function HasDirectOverride(uuid)
    return ConfigUtils.HasDirectOverride(activeConfig, uuid)
end

local function GetInheritedConfigValue(itemData)
    if not itemData or itemData.templateScope ~= "Local" then return nil end
    return ConfigUtils.GetInheritedValue(activeConfig, itemData.rootTemplateId)
end

local function GetEffectiveConfigValue(itemData)
    if not itemData then return nil end
    local rootTemplateId = itemData.templateScope == "Local" and itemData.rootTemplateId or nil
    return ConfigUtils.GetEffectiveValue(activeConfig, itemData.uuid, rootTemplateId)
end

local function GetCurrentSetting(itemData)
    return GetEffectiveConfigValue(itemData) or itemData.defaultTooltip
end

local function HasInheritedRootConfig(itemData)
    return itemData
        and itemData.templateScope == "Local"
        and not HasDirectOverride(itemData.uuid)
        and GetInheritedConfigValue(itemData) ~= nil
end

local function SetConfigValue(uuid, newValue, originalValue)
    activeConfig[uuid] = { newValue, originalValue }
end

local function IsEdited(uuid)
    return ConfigUtils.IsEdited(activeConfig, uuid)
end

local function ClearConfigValue(uuid)
    activeConfig[uuid] = nil
end

local function ApplyItemSelection(itemData, newSelection)
    local uuid = itemData.uuid
    local originalValue = GetOriginalValue(uuid) or itemData.defaultTooltip
    local inheritedValue = GetInheritedConfigValue(itemData)
    if inheritedValue ~= nil then
        if newSelection == inheritedValue then
            ClearConfigValue(uuid)
        else
            SetConfigValue(uuid, newSelection, originalValue)
        end
    else
        if newSelection == originalValue then
            ClearConfigValue(uuid)
        else
            SetConfigValue(uuid, newSelection, originalValue)
        end
    end
end

local function SaveConfig()
    Ext.IO.SaveFile(modFolderPath .. "/config.json", Ext.Json.Stringify(masterConfig))
    local CHUNK_SIZE = 500
    local keys = {}
    for k, _ in pairs(activeConfig) do table.insert(keys, k) end
    local totalChunks = math.max(1, math.ceil(#keys / CHUNK_SIZE))
    for chunkIndex = 1, totalChunks do
        local chunk = {}
        local startIdx = (chunkIndex - 1) * CHUNK_SIZE + 1
        local endIdx = math.min(chunkIndex * CHUNK_SIZE, #keys)
        for i = startIdx, endIdx do
            chunk[keys[i]] = activeConfig[keys[i]]
        end
        local message = { chunkIndex = chunkIndex, totalChunks = totalChunks, config = chunk }
        local json = Ext.Json.Stringify(message)
        Ext.ClientNet.PostMessageToServer("TooltipManager_ApplyConfigChunk", json)
    end
end

local function GetPresetNames()
    local names = {}
    if masterConfig.presets then for name, _ in pairs(masterConfig.presets) do table.insert(names, name) end end
    table.sort(names)
    return names
end

local function SetActivePreset(presetName)
    if masterConfig.presets[presetName] then
        masterConfig.activePresetName = presetName
        activeConfig = masterConfig.presets[presetName]
    end
end

local function ClearChildren(parent)
    if not (parent and parent.Children) then return end
    local childrenToDestroy = {}
    for _, child in ipairs(parent.Children) do
        local isHeader = false
        local success, value = pcall(function() return child.Headers end)
        if success and value == true then isHeader = true end
        if not isHeader then table.insert(childrenToDestroy, child) end
    end
    for _, child in ipairs(childrenToDestroy) do child:Destroy() end
end

local function SettingValueToText(value)
    if value == 0 then
        return "Hidden (0)"
    elseif value == 1 then
        return "On Hover (1)"
    elseif value == 2 then
        return "Alt-Highlight (2)"
    else
        return "Unknown"
    end
end

local function GetConfigKey(itemData)
    return itemData.uuid
end

local function PopulateTooltip(tooltip, itemData)
    if not tooltip or not itemData then return end
    tooltip:AddText("UUID: " .. itemData.uuid)
    if itemData.rootTemplateId then
        tooltip:AddText("Root Template: " .. itemData.rootTemplateId)
    end
    tooltip:AddSeparator()
    tooltip:AddText("Source Mod: " .. itemData.sourceMod)
    tooltip:AddText("Item Type: " .. itemData.itemType)
    tooltip:AddText("Template Scope: " .. (itemData.templateScope or "Unknown"))
    tooltip:AddText("Is Lootable: " .. tostring(itemData.canBePickedUp))
    tooltip:AddText("Is Container: " .. tostring(itemData.isContainer))
    if HasInheritedRootConfig(itemData) then
        tooltip:AddSeparator()
        local inheritedText = tooltip:AddText("Inherited Setting: " .. SettingValueToText(GetInheritedConfigValue(itemData)))
        inheritedText:SetColor("Text", { 0.6, 0.7, 1.0, 1.0 })
    elseif itemData.templateScope == "Local" and HasDirectOverride(itemData.uuid) then
        tooltip:AddSeparator()
        local overrideText = tooltip:AddText("Local template override is active.")
        overrideText:SetColor("Text", { 1.0, 0.8, 0.4, 1.0 })
    end
    if IsEdited(GetConfigKey(itemData)) then
        tooltip:AddSeparator()
        local originalValue = GetOriginalValue(GetConfigKey(itemData))
        local currentValue = GetConfigValue(GetConfigKey(itemData))
        local originalText = SettingValueToText(originalValue)
        local newText = SettingValueToText(currentValue)
        tooltip:AddText("Original: " .. originalText)
        local changedText = tooltip:AddText("Changed To: " .. newText)
        changedText:SetColor("Text", { 0.2, 1.0, 0.2, 1.0 })
    end
end

local function RefreshItemList()
    if not itemsTable or not searchInput then return end
    local rawSearchText = searchInput.Text or ""
    local searchText = string.lower(rawSearchText)
    local tempFiltered = {}
    for _, itemData in ipairs(itemTemplatesCache) do
        local textMatches = false
        if searchText == "" then
            textMatches = true
        else
            local searchTarget = string.lower(tostring(itemData.displayName)) ..
                "\t" .. string.lower(tostring(itemData.internalName)) .. "\t" .. string.lower(tostring(itemData.uuid))
            if searchText:sub(1, 1) == '"' and searchText:sub(-1) == '"' and searchText:len() > 2 then
                local word = searchText:sub(2, -2)
                if string.find(searchTarget, "%f[%w]" .. word .. "%f[%W]") then textMatches = true end
            else
                if string.find(searchTarget, searchText, 1, true) then textMatches = true end
            end
        end
        if not textMatches then goto continue end
        if filterOptions.editedStatus == "Edited Only" and not IsEdited(GetConfigKey(itemData)) then goto continue end
        if filterOptions.editedStatus == "Unedited Only" and IsEdited(GetConfigKey(itemData)) then goto continue end
        if filterOptions.modStatus == "Vanilla Only" and itemData.sourceMod ~= "Vanilla" then goto continue end
        if filterOptions.modStatus == "Modded Only" and itemData.sourceMod == "Vanilla" then goto continue end
        if filterOptions.lootableStatus == "Lootable" and not itemData.canBePickedUp then goto continue end
        if filterOptions.lootableStatus == "Not Lootable" and itemData.canBePickedUp then goto continue end
        if filterOptions.containerStatus == "Containers Only" and not itemData.isContainer then goto continue end
        if filterOptions.containerStatus == "Non-Containers" and itemData.isContainer then goto continue end
        if filterOptions.itemType ~= "All" and itemData.itemType ~= filterOptions.itemType then goto continue end
        if filterOptions.sourceMod ~= "All" and itemData.sourceMod ~= filterOptions.sourceMod then goto continue end
        if filterOptions.visibilityState ~= "All" then
            local currentState = GetCurrentSetting(itemData)
            if filterOptions.visibilityState == "Hidden" and currentState ~= 0 then goto continue end
            if filterOptions.visibilityState == "On Hover" and currentState ~= 1 then goto continue end
            if filterOptions.visibilityState == "Alt-Highlight" and currentState ~= 2 then goto continue end
        end
        if filterOptions.templateScope ~= "All" and itemData.templateScope ~= filterOptions.templateScope then goto continue end
        table.insert(tempFiltered, itemData)
        ::continue::
    end
    filteredItemList = tempFiltered
    ClearChildren(itemsTable)
    for _, itemData in ipairs(filteredItemList) do
        local row = itemsTable:AddRow()
        local currentSetting = GetCurrentSetting(itemData)
        local isLocal = itemData.templateScope == "Local"
        if currentSetting == 0 then
            if isLocal then
                row:SetColor("TableRowBg", { 0.3, 0.2, 0.25, 1.0 }); row:SetColor("TableRowBgAlt",
                    { 0.3, 0.2, 0.25, 1.0 })
            else
                row:SetColor("TableRowBg", { 0.3, 0.2, 0.2, 1.0 }); row:SetColor("TableRowBgAlt", { 0.3, 0.2, 0.2, 1.0 })
            end
        elseif currentSetting == 2 then
            if isLocal then
                row:SetColor("TableRowBg", { 0.2, 0.25, 0.4, 1.0 }); row:SetColor("TableRowBgAlt",
                    { 0.2, 0.25, 0.4, 1.0 })
            else
                row:SetColor("TableRowBg", { 0.2, 0.25, 0.35, 1.0 }); row:SetColor("TableRowBgAlt",
                    { 0.2, 0.25, 0.35, 1.0 })
            end
        else
            if isLocal then
                row:SetColor("TableRowBg", { 0.22, 0.22, 0.28, 1.0 }); row:SetColor("TableRowBgAlt",
                    { 0.22, 0.22, 0.28, 1.0 })
            else
                row:SetColor("TableRowBg", { 0.22, 0.22, 0.22, 1.0 }); row:SetColor("TableRowBgAlt",
                    { 0.22, 0.22, 0.22, 1.0 })
            end
        end
        local statusCell = row:AddCell()
        if IsEdited(GetConfigKey(itemData)) then
            local statusText = statusCell:AddText("Edited")
            statusText:SetColor("Text", { 0.2, 1.0, 0.2, 1.0 })
            PopulateTooltip(statusText:Tooltip(), itemData)
        elseif HasInheritedRootConfig(itemData) then
            local statusText = statusCell:AddText("Root")
            statusText:SetColor("Text", { 0.6, 0.7, 1.0, 1.0 })
            PopulateTooltip(statusText:Tooltip(), itemData)
        elseif itemData.templateScope == "Local" and HasDirectOverride(itemData.uuid) then
            local statusText = statusCell:AddText("Local")
            statusText:SetColor("Text", { 1.0, 0.8, 0.4, 1.0 })
            PopulateTooltip(statusText:Tooltip(), itemData)
        end
        local iconCell = row:AddCell()
        if itemData.icon and itemData.icon ~= "" and not iconBlacklist[itemData.icon] then
            local icon = iconCell:AddImage(itemData.icon, { 32, 32 })
            PopulateTooltip(icon:Tooltip(), itemData)
        end
        local nameCell = row:AddCell()
        local displayName = itemData.displayName
        if isLocal then displayName = displayName .. " (LOCAL)" end
        local nameText = nameCell:AddText(displayName)
        if isLocal then nameText:SetColor("Text", { 0.6, 0.7, 1.0, 1.0 }) end
        PopulateTooltip(nameText:Tooltip(), itemData)
        local internalNameCell = row:AddCell()
        local internalNameText = internalNameCell:AddText(itemData.internalName)
        PopulateTooltip(internalNameText:Tooltip(), itemData)
        local optionsCell = row:AddCell()
        local combo = optionsCell:AddCombo("##" .. itemData.uuid)
        combo.Options = { "Hidden (0)", "On Hover (1)", "Alt-Highlight (2)" }
        combo.SelectedIndex = currentSetting
        combo.OnChange = function(c)
            local newSelection = c.SelectedIndex
            ApplyItemSelection(itemData, newSelection)
            SaveConfig()
            Ext.Timer.WaitFor(1, RefreshItemList)
        end
    end
    if itemCountText then
        itemCountText.Text = string.format("Showing %d / %d items", #filteredItemList, #itemTemplatesCache)
    end
end

local function RebuildFilterUI()
    if not filterGroup then return end
    ClearChildren(filterGroup)
    local group1 = filterGroup:AddGroup("FilterGroup1")
    local editedCombo = group1:AddCombo("##EditedFilter")
    editedCombo.Options = { "All", "Edited Only", "Unedited Only" }; editedCombo.ItemWidth = 150
    for i, v in ipairs(editedCombo.Options) do if v == filterOptions.editedStatus then editedCombo.SelectedIndex = i - 1 end end
    editedCombo.OnChange = function(c)
        filterOptions.editedStatus = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    editedCombo:Tooltip():AddText("Filter by whether items have been edited in the active preset.")
    local modCombo = group1:AddCombo("##ModFilter"); modCombo.SameLine = true
    modCombo.Options = { "All", "Vanilla Only", "Modded Only" }; modCombo.ItemWidth = 150
    for i, v in ipairs(modCombo.Options) do if v == filterOptions.modStatus then modCombo.SelectedIndex = i - 1 end end
    modCombo.OnChange = function(c)
        filterOptions.modStatus = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    modCombo:Tooltip():AddText("Filter by whether items are from the base game or from other mods.")
    local lootableCombo = group1:AddCombo("##LootableFilter"); lootableCombo.SameLine = true
    lootableCombo.Options = { "All", "Lootable", "Not Lootable" }; lootableCombo.ItemWidth = 150
    for i, v in ipairs(lootableCombo.Options) do
        if v == filterOptions.lootableStatus then
            lootableCombo.SelectedIndex =
                i - 1
        end
    end
    lootableCombo.OnChange = function(c)
        filterOptions.lootableStatus = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    lootableCombo:Tooltip():AddText("Filter by whether an item can be picked up by the player.")
    local containerCombo = group1:AddCombo("##ContainerFilter"); containerCombo.SameLine = true
    containerCombo.Options = { "All", "Containers Only", "Non-Containers" }; containerCombo.ItemWidth = 150
    for i, v in ipairs(containerCombo.Options) do
        if v == filterOptions.containerStatus then
            containerCombo.SelectedIndex =
                i - 1
        end
    end
    containerCombo.OnChange = function(c)
        filterOptions.containerStatus = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    containerCombo:Tooltip():AddText("Filter by whether an item is a container.")
    local visibilityCombo = group1:AddCombo("##VisibilityFilter"); visibilityCombo.SameLine = true
    visibilityCombo.Options = { "All", "Hidden", "On Hover", "Alt-Highlight" }; visibilityCombo.ItemWidth = 150
    for i, v in ipairs(visibilityCombo.Options) do
        if v == filterOptions.visibilityState then
            visibilityCombo.SelectedIndex =
                i - 1
        end
    end
    visibilityCombo.OnChange = function(c)
        filterOptions.visibilityState = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    visibilityCombo:Tooltip():AddText("Filter by the item's current visibility state.")
    local group2 = filterGroup:AddGroup("FilterGroup2")
    local typeCombo = group2:AddCombo("##TypeFilter")
    typeCombo.Options = allItemTypes; typeCombo.ItemWidth = 200
    for i, v in ipairs(typeCombo.Options) do if v == filterOptions.itemType then typeCombo.SelectedIndex = i - 1 end end
    typeCombo.OnChange = function(c)
        filterOptions.itemType = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    typeCombo:Tooltip():AddText("Filter by the item's general category.")
    local sourceModCombo = group2:AddCombo("##SourceModFilter"); sourceModCombo.SameLine = true
    sourceModCombo.Options = allSourceMods; sourceModCombo.ItemWidth = 200
    for i, v in ipairs(sourceModCombo.Options) do
        if v == filterOptions.sourceMod then
            sourceModCombo.SelectedIndex = i -
                1
        end
    end
    sourceModCombo.OnChange = function(c)
        filterOptions.sourceMod = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    sourceModCombo:Tooltip():AddText("Filter by the specific mod an item originates from.")
    local scopeCombo = group2:AddCombo("##ScopeFilter"); scopeCombo.SameLine = true
    scopeCombo.Options = { "All", "Root", "Local" }; scopeCombo.ItemWidth = 120
    for i, v in ipairs(scopeCombo.Options) do
        if v == filterOptions.templateScope then scopeCombo.SelectedIndex = i - 1 end
    end
    scopeCombo.OnChange = function(c)
        filterOptions.templateScope = c.Options[c.SelectedIndex + 1]; RefreshItemList()
    end
    scopeCombo:Tooltip():AddText(
        "Filter by template scope.\n\nNote: Local templates only show items currently loaded in the world. Fast travel or enter new areas to load more.")
end

local function RefreshUI()
    if not presetCombo then return end
    local presetNames = GetPresetNames()
    local activePresetIndex = 1
    for i, name in ipairs(presetNames) do if name == masterConfig.activePresetName then activePresetIndex = i end end
    presetCombo.Options = presetNames
    presetCombo.SelectedIndex = activePresetIndex - 1
    if deletePresetBtn then
        deletePresetBtn.Disabled = (masterConfig.activePresetName == "Default")
        local tooltip = deletePresetBtn:Tooltip()
        ClearChildren(tooltip)
        if deletePresetBtn.Disabled then
            tooltip:AddText("The 'Default' preset cannot be deleted.")
        else
            tooltip:AddText("Deletes the currently selected preset. This cannot be undone.")
        end
    end
    if isTableLoaded then
        RebuildFilterUI()
        RefreshItemList()
    end
end

local function BuildManagerUI(tab)
    local mainControlsHeader = tab:AddCollapsingHeader("Item Filters & Actions")
    mainControlsHeader.DefaultOpen = true
    mainControlsHeader:AddSeparator()
    mainControlsHeader:AddText("Filter:")
    filterGroup = mainControlsHeader:AddGroup("FilterGroup")
    mainControlsHeader:AddSeparator()
    local actionGroup = mainControlsHeader:AddGroup("ActionButtons")
    local refreshBtn = actionGroup:AddButton("Refresh List"); refreshBtn.SameLine = true
    local resetBtn = actionGroup:AddButton("Reset Current Preset"); resetBtn.SameLine = true; resetBtn:SetColor("Button",
        { 0.8, 0.2, 0.2, 1 })
    actionGroup:AddText(" | Apply to filtered:")
    actionGroup.SameLine = true
    local setAllHoverBtn = actionGroup:AddButton("Set to Hover"); setAllHoverBtn.SameLine = true
    local setAllHighlightBtn = actionGroup:AddButton("Set to Highlight"); setAllHighlightBtn.SameLine = true
    local setAllHiddenBtn = actionGroup:AddButton("Set to Hidden"); setAllHiddenBtn.SameLine = true
    mainControlsHeader:AddSeparator()
    searchInput = mainControlsHeader:AddInputText("Search", "")
    searchInput.Hint = "Search by name or UUID. Use \"quotes\" for whole-word search..."
    searchInput.OnChange = function()
        if searchDebounceTimer then Ext.Timer.Cancel(searchDebounceTimer) end
        searchDebounceTimer = Ext.Timer.WaitFor(250, RefreshItemList)
    end
    itemCountText = mainControlsHeader:AddInputText("##ItemCount", "Showing 0 / 0 items")
    itemCountText.ReadOnly = true
    itemCountText:SetColor("FrameBg", { 0, 0, 0, 0 })
    itemsTable = tab:AddTable("TooltipItemsTable", 5)
    itemsTable.Borders = true; itemsTable.RowBg = true; itemsTable.ScrollY = true; itemsTable.Size = { 0, 600 }
    itemsTable:AddColumn("Status", "WidthFixed", 60)
    itemsTable:AddColumn("Icon", "WidthFixed", 40)
    itemsTable:AddColumn("Display Name", "WidthStretch", 1.0)
    itemsTable:AddColumn("Internal Name", "WidthStretch", 0.8)
    itemsTable:AddColumn("Visibility", "WidthFixed", 250)
    local headerRow = itemsTable:AddRow()
    headerRow.Headers = true
    headerRow:AddCell():AddText("Status"); headerRow:AddCell():AddText("Icon"); headerRow:AddCell():AddText(
        "Display Name")
    headerRow:AddCell():AddText("Internal Name"); headerRow:AddCell():AddText("Visibility")
    refreshBtn.OnClick = function() RefreshUI() end
    setAllHoverBtn.OnClick = function()
        for _, d in ipairs(filteredItemList) do ApplyItemSelection(d, 1) end
        SaveConfig(); RefreshItemList()
    end
    setAllHighlightBtn.OnClick = function()
        for _, d in ipairs(filteredItemList) do ApplyItemSelection(d, 2) end
        SaveConfig(); RefreshItemList()
    end
    setAllHiddenBtn.OnClick = function()
        for _, d in ipairs(filteredItemList) do ApplyItemSelection(d, 0) end
        SaveConfig(); RefreshItemList()
    end
    resetBtn.OnClick = function()
        local templateMap = {}
        for _, item in ipairs(itemTemplatesCache) do
            templateMap[item.uuid] = item
        end
        for uuid, entry in pairs(activeConfig) do
            if type(entry) == "table" and entry[2] ~= nil then
                local original = entry[2]
                if templateMap[uuid] then
                    templateMap[uuid].defaultTooltip = original
                end
                SetConfigValue(uuid, original, original)
            end
        end
        SaveConfig()
        masterConfig.presets[masterConfig.activePresetName] = {}
        activeConfig = masterConfig.presets[masterConfig.activePresetName]
        SaveConfig()
        RefreshUI()
    end
    RefreshUI()
end

local function SetupMCM()
    if TooltipManagerTab ~= nil or not Mods.BG3MCM then return end
    Mods.BG3MCM.IMGUIAPI:InsertModMenuTab(ModuleUUID, "Tooltip Manager", function(tab)
        TooltipManagerTab = tab
        tab:AddText("Configure tooltip visibility for items.")
        tab:AddSeparator()
        local presetHeader = tab:AddCollapsingHeader("Preset Management")
        presetHeader:AddText("Active Preset:")
        presetCombo = presetHeader:AddCombo("##ActivePreset")
        local presetNames = GetPresetNames()
        presetCombo.Options = presetNames
        for i, name in ipairs(presetNames) do
            if name == masterConfig.activePresetName then
                presetCombo.SelectedIndex = i -
                    1
            end
        end
        presetCombo:Tooltip():AddText("Select which group of settings to use.")
        presetCombo.OnChange = function(c)
            SetActivePreset(c.Options[c.SelectedIndex + 1]); SaveConfig(); if isTableLoaded then RefreshUI() end
        end
        presetHeader:AddSeparator()
        local savePresetInput = presetHeader:AddInputText("New Preset Name", "")
        local savePresetBtn = presetHeader:AddButton("Save Current Settings as New Preset")
        savePresetBtn.OnClick = function()
            local newName = savePresetInput.Text
            if newName and newName ~= "" and not masterConfig.presets[newName] then
                local newPresetData = {}; for k, v in pairs(activeConfig) do newPresetData[k] = v end
                masterConfig.presets[newName] = newPresetData
                SetActivePreset(newName); SaveConfig(); RefreshUI()
            end
        end
        deletePresetBtn = presetHeader:AddButton("Delete Current Preset")
        deletePresetBtn.OnClick = function()
            if masterConfig.activePresetName ~= "Default" then
                masterConfig.presets[masterConfig.activePresetName] = nil
                SetActivePreset("Default"); SaveConfig(); RefreshUI()
            end
        end
        local importExportHeader = tab:AddCollapsingHeader("Import / Export Presets")
        local presetFolderPath = modFolderPath .. "/Presets"
        importExportStatusText = importExportHeader:AddInputText("##StatusLabel",
            "Share presets by exporting/importing them as files.")
        importExportStatusText.ReadOnly = true; importExportStatusText:SetColor("FrameBg", { 0, 0, 0, 0 })
        importExportHeader:AddSeparator()
        importExportHeader:AddText("Export Current Preset As:")
        local exportNameInput = importExportHeader:AddInputText("##ExportName", masterConfig.activePresetName)
        exportNameInput.Hint = "Enter filename here"
        local exportBtn = importExportHeader:AddButton("Export to File")
        exportBtn.OnClick = function()
            local desiredName = exportNameInput.Text
            if desiredName and desiredName ~= "" then
                local finalFilename = desiredName
                if not finalFilename:match("%.json$") then finalFilename = finalFilename .. ".json" end
                local path = presetFolderPath .. "/" .. finalFilename
                if Ext.IO.SaveFile(path, Ext.Json.Stringify(activeConfig)) then
                    importExportStatusText.Text = "Exported '" .. finalFilename .. "' successfully."
                    importExportStatusText:SetColor("Text", { 0.2, 1.0, 0.2, 1.0 })
                else
                    importExportStatusText.Text = "Error: Failed to export file."
                    importExportStatusText:SetColor("Text", { 1.0, 0.2, 0.2, 1.0 })
                end
            end
        end
        importExportHeader:AddSeparator()
        importExportHeader:AddText("Import Preset from File:")
        local importFilenameInput = importExportHeader:AddInputText("##ImportFilename", "")
        importFilenameInput.Hint = "Type filename here (e.g., MyPreset or MyPreset.json)"
        local importBtn = importExportHeader:AddButton("Import from File")
        importBtn.OnClick = function()
            local desiredName = importFilenameInput.Text
            if not desiredName or desiredName == "" then
                importExportStatusText.Text = "Error: Please enter a filename to import."; importExportStatusText
                    :SetColor("Text", { 1.0, 0.2, 0.2, 1.0 }); return
            end
            local finalFilename = desiredName
            if not finalFilename:match("%.json$") then finalFilename = finalFilename .. ".json" end
            local presetName = finalFilename:gsub("%.json$", "")
            if masterConfig.presets[presetName] then
                importExportStatusText.Text = "Error: A preset named '" .. presetName .. "' already exists."; importExportStatusText
                    :SetColor("Text", { 1.0, 0.2, 0.2, 1.0 }); return
            end
            local path = presetFolderPath .. "/" .. finalFilename
            local jsonString = Ext.IO.LoadFile(path)
            if jsonString and jsonString ~= "" then
                local success, presetData = pcall(Ext.Json.Parse, jsonString)
                if success and type(presetData) == "table" then
                    masterConfig.presets[presetName] = presetData; SetActivePreset(presetName); SaveConfig()
                    importExportStatusText.Text = "Imported '" .. presetName .. "' successfully."
                    importExportStatusText:SetColor("Text", { 0.2, 1.0, 0.2, 1.0 }); RefreshUI()
                else
                    importExportStatusText.Text = "Error: Could not parse file data."
                    importExportStatusText:SetColor("Text", { 1.0, 0.2, 0.2, 1.0 })
                end
            else
                importExportStatusText.Text = "Error: File not found or is empty. Check the filename."
                importExportStatusText:SetColor("Text", { 1.0, 0.2, 0.2, 1.0 })
            end
        end
        tab:AddSeparator()
        mainContentHolder = tab:AddGroup("MainContentHolder")
        local disclaimer = mainContentHolder:AddText(
            "Note: Local templates only show items currently loaded in the world. Fast travel or enter new areas to load more.")
        disclaimer:SetColor("Text", { 0.7, 0.7, 0.5, 1.0 })
        local loadBtn = mainContentHolder:AddButton("Load Items")
        loadBtn.Size = { 0, 50 }
        loadBtn:Tooltip():AddText(
            "Request latest templates from server. Local templates will reflect currently loaded world areas.")
        loadBtn.OnClick = function()
            isTableLoaded = true
            ClearChildren(mainContentHolder)
            Ext.ClientNet.PostMessageToServer("TooltipManager_RequestTemplates", "")
            BuildManagerUI(mainContentHolder)
        end
    end)
end

ReadConfig()
SetupMCM()

local receivedChunks = 0
local expectedChunks = 0
local pendingTemplates = {}

Ext.RegisterNetListener("TooltipManager_ReceiveChunk", function(channel, payload)
    local success, data = pcall(Ext.Json.Parse, payload)
    if not success or type(data) ~= "table" then return end
    if data.chunkIndex == 1 then
        pendingTemplates = {}
        receivedChunks = 0
        expectedChunks = data.totalChunks
    end
    for _, item in ipairs(data.templates) do
        item.templateScope = data.scope
        table.insert(pendingTemplates, item)
    end
    receivedChunks = receivedChunks + 1
    if receivedChunks >= expectedChunks then
        itemTemplatesCache = pendingTemplates
        local uniqueItemTypes = {}
        local uniqueSourceMods = {}
        local rootCount = 0
        local localCount = 0
        for _, item in ipairs(itemTemplatesCache) do
            uniqueItemTypes[item.itemType] = true
            uniqueSourceMods[item.sourceMod] = true
            if item.templateScope == "Root" then rootCount = rootCount + 1 else localCount = localCount + 1 end
        end
        allItemTypes = { "All" }
        allSourceMods = { "All" }
        for typeName, _ in pairs(uniqueItemTypes) do table.insert(allItemTypes, typeName) end
        for modName, _ in pairs(uniqueSourceMods) do table.insert(allSourceMods, modName) end
        table.sort(allItemTypes)
        table.sort(allSourceMods)
        table.sort(itemTemplatesCache, function(a, b) return a.displayName < b.displayName end)
        if isTableLoaded then
            RebuildFilterUI()
            RefreshItemList()
        end
        pendingTemplates = {}
    end
end)

Ext.Events.SessionLoaded:Subscribe(function()
    if activeConfig then
        local CHUNK_SIZE = 500
        local keys = {}
        for k, _ in pairs(activeConfig) do table.insert(keys, k) end
        local totalChunks = math.max(1, math.ceil(#keys / CHUNK_SIZE))
        for chunkIndex = 1, totalChunks do
            local chunk = {}
            local startIdx = (chunkIndex - 1) * CHUNK_SIZE + 1
            local endIdx = math.min(chunkIndex * CHUNK_SIZE, #keys)
            for i = startIdx, endIdx do
                chunk[keys[i]] = activeConfig[keys[i]]
            end
            local message = { chunkIndex = chunkIndex, totalChunks = totalChunks, config = chunk }
            local json = Ext.Json.Stringify(message)
            Ext.ClientNet.PostMessageToServer("TooltipManager_ApplyConfigChunk", json)
        end
    end
    if TooltipManagerTab then
        TooltipManagerTab:Destroy()
        TooltipManagerTab = nil
        SetupMCM()
    end
end)

Ext.ModEvents.BG3MCM["MCM_Window_Closed"]:Subscribe(function(payload)
    if isTableLoaded then
        isTableLoaded = false
        filteredItemList = {}
        if mainContentHolder then
            ClearChildren(mainContentHolder)
            local disclaimer = mainContentHolder:AddText(
                "Note: Local templates only show items currently loaded in the world. Fast travel or enter new areas to load more.")
            disclaimer:SetColor("Text", { 0.7, 0.7, 0.5, 1.0 })
            local loadBtn = mainContentHolder:AddButton("Load Items")
            loadBtn.Size = { 0, 50 }
            loadBtn.OnClick = function()
                isTableLoaded = true
                ClearChildren(mainContentHolder)
                Ext.ClientNet.PostMessageToServer("TooltipManager_RequestTemplates", "")
                BuildManagerUI(mainContentHolder)
            end
        end
    end
end)
