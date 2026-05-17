local ConfigUtils = {}

function ConfigUtils.GetEntryValue(entry)
    if entry == nil then return nil end
    if type(entry) == "table" then return entry[1] end
    return entry
end

function ConfigUtils.GetEntryOriginalValue(entry)
    if entry == nil then return nil end
    if type(entry) == "table" then return entry[2] end
    return entry
end

function ConfigUtils.HasDirectOverride(config, uuid)
    return config[uuid] ~= nil
end

function ConfigUtils.GetInheritedValue(config, rootTemplateId)
    if not rootTemplateId or rootTemplateId == "" then return nil end
    return ConfigUtils.GetEntryValue(config[rootTemplateId])
end

function ConfigUtils.GetEffectiveValue(config, uuid, rootTemplateId)
    local directValue = ConfigUtils.GetEntryValue(config[uuid])
    if directValue ~= nil then return directValue end
    return ConfigUtils.GetInheritedValue(config, rootTemplateId)
end

function ConfigUtils.IsEdited(config, uuid)
    local entry = config[uuid]
    if entry == nil then return false end
    if type(entry) == "table" then
        return entry[1] ~= entry[2]
    end
    return false
end

return ConfigUtils
