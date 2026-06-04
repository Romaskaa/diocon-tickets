from .vo import UserRole

# Группы ролей для удобных проверок

# Все роли, относящиеся к заказчикам
CUSTOMER_ROLES = {UserRole.CUSTOMER, UserRole.CUSTOMER_ADMIN}

# Все роли внутренней команды
INTERNAL_ROLES = {
    UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN
}

# Роли с правами администратора заказчика и выше
CUSTOMER_ADMIN_AND_ABOVE = {
    UserRole.CUSTOMER_ADMIN,
    UserRole.SUPPORT_AGENT,
    UserRole.SUPPORT_MANAGER,
    UserRole.ADMIN,
}

# Роли с правами менеджера поддержки и выше
SUPPORT_MANAGER_OR_ABOVE = {UserRole.SUPPORT_MANAGER, UserRole.ADMIN}

# Роли команды поддержки
SUPPORT_TEAM = {UserRole.SUPPORT_AGENT, UserRole.SUPPORT_MANAGER, UserRole.ADMIN}
