import operator

ORG_FULL_NAME = "org_full_name"
ORG_HIERARCHY_X = "org_hierarchy_x"
ORG_HIERARCHY_Y = "org_hierarchy_y"
OPERATOR_MAPPING = {
    "以上": operator.ge,
    "より大きい": operator.gt,
    "以下": operator.le,
    "より小さい": operator.lt,
    "等しい": operator.eq,
    "等しくない": operator.ne,
}
OTHER_LABEL = "その他"
