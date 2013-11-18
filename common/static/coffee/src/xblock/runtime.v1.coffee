@XBlock.runtime.v1 = (element, children) ->
  childMap = {}
  $.each children, (idx, child) ->
    childMap[child.name] = child

  return {
    handlerUrl: (element, handlerName, suffix, query) ->
      handlerPrefix = $(element).data("handler-prefix")
      suffix = if suffix? then "/#{suffix}" else ''
      query = if query? then "?#{query}" else ''
      "#{handlerPrefix}/#{handlerName}#{suffix}#{query}"
    children: children
    childMap: childMap
  }
