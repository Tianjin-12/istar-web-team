from django.contrib import admin
from mvp.models import Mention_percentage, LinkCategory, AILink


@admin.register(Mention_percentage)
class Mention_percentageAdmin(admin.ModelAdmin):
    list_display = (
        "brand_name",
        "keyword_name",
        "brand_amount",
        "high_relevance_ratio",
        "created_at",
    )
    search_fields = ("brand_name", "keyword_name")
    list_filter = ("brand_name", "keyword_name")


@admin.register(LinkCategory)
class LinkCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "relevance_level", "order", "color")
    ordering = ("order", "-relevance_level")
    search_fields = ("name",)


@admin.register(AILink)
class AILinkAdmin(admin.ModelAdmin):
    list_display = ("id", "link_url", "category", "is_manual", "created_at")
    list_filter = ("category", "is_manual")
    search_fields = ("link_url",)
    raw_id_fields = ("answer",)
    list_per_page = 50
    actions = ["bulk_set_category"]

    @admin.action(description="批量设置选中链接的分类")
    def bulk_set_category(self, request, queryset):
        from django import forms
        from django.shortcuts import render, redirect
        from django.contrib import messages

        class CategoryForm(forms.Form):
            category = forms.ModelChoiceField(
                queryset=LinkCategory.objects.all(),
                label="选择分类",
            )

        if "apply" in request.POST:
            form = CategoryForm(request.POST)
            if form.is_valid():
                category = form.cleaned_data["category"]
                updated = queryset.update(category=category, is_manual=True)
                messages.success(
                    request, f"已更新 {updated} 条链接的分类为「{category.name}」"
                )
                return redirect(request.get_full_path())
        else:
            form = CategoryForm()

        return render(
            request,
            "admin/bulk_set_category.html",
            {
                "form": form,
                "queryset": queryset,
                "ids": ",".join(str(q.id) for q in queryset),
            },
        )
