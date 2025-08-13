export function renderPagination(container, currentPage, totalItems, limit, onPageChange) {
    container.innerHTML = '';
    const totalPages = Math.ceil(totalItems / limit);

    if (totalPages <= 1) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'pagination-wrapper';

    // Previous Button
    const prevButton = document.createElement('button');
    prevButton.textContent = '« Prev';
    prevButton.disabled = currentPage === 1;
    prevButton.addEventListener('click', () => onPageChange(currentPage - 1));
    wrapper.appendChild(prevButton);

    // Page indicator
    const pageInfo = document.createElement('span');
    pageInfo.className = 'page-info';
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    wrapper.appendChild(pageInfo);

    // Next Button
    const nextButton = document.createElement('button');
    nextButton.textContent = 'Next »';
    nextButton.disabled = currentPage === totalPages;
    nextButton.addEventListener('click', () => onPageChange(currentPage + 1));
    wrapper.appendChild(nextButton);

    container.appendChild(wrapper);
}